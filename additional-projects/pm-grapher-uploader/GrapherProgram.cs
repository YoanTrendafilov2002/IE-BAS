using System.Globalization;
using System.Reflection;
using SkiaSharp;

internal static class GrapherProgram
{
    private const string InputEnvironmentVariable = "FTPPM_INPUT_DIR";
    private const string OutputEnvironmentVariable = "FTPPM_OUTPUT_DIR";
    private const string DataFilePattern = "DUSTMONITOR_20746_*.txt";
    private const int TailBytes = 4_000_000;

    private static readonly List<Sample> Samples = new();
    private static string InputDir = string.Empty;
    private static string OutputDir = string.Empty;
    private static string ArchiveDir = string.Empty;

    private static async Task<int> Main(string[] args)
    {
        bool runOnce = args.Any(a => a.Equals("--once", StringComparison.OrdinalIgnoreCase));
        bool dryRun = args.Any(a => a.Equals("--dry-run", StringComparison.OrdinalIgnoreCase));
        bool disableAutoStart = args.Any(a => a.Equals("--no-autostart", StringComparison.OrdinalIgnoreCase));

        InputDir = ResolveInputDirectory();
        OutputDir = ResolveOutputDirectory();
        ArchiveDir = Path.Combine(OutputDir, "PMarchive");
        Environment.SetEnvironmentVariable("FTPPM_LOCAL_DIR", OutputDir);

        EnsureSkiaNativeLibrary();

        Directory.CreateDirectory(OutputDir);
        Directory.CreateDirectory(ArchiveDir);

        if (!dryRun && !disableAutoStart)
            EnsureStartsWithWindows();

        using var instanceLock = AcquireInstanceLock();
        if (instanceLock is null)
        {
            Console.WriteLine("PMGrapherUploader is already running.");
            return 0;
        }

        Console.WriteLine("PMGrapherUploader started.");
        Console.WriteLine("Data directory: " + InputDir);
        Console.WriteLine("Graph directory: " + OutputDir);
        Console.WriteLine(dryRun ? "Dry run: FTP upload is disabled." : "FTP upload is enabled.");

        while (true)
        {
            try
            {
                await GenerateGraphsAndUpload(dryRun);
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Cycle failed at {DateTime.UtcNow:yyyy-MM-dd HH:mm:ss} UTC:");
                Console.WriteLine(ex);
            }

            if (runOnce)
                return 0;

            await WaitUntilNextHourUtc();
        }
    }

    private static FileStream? AcquireInstanceLock()
    {
        try
        {
            string lockPath = Path.Combine(OutputDir, "pm-grapher-uploader.lock");
            return new FileStream(lockPath, FileMode.OpenOrCreate, FileAccess.ReadWrite, FileShare.None);
        }
        catch (IOException)
        {
            return null;
        }
    }

    private static void EnsureSkiaNativeLibrary()
    {
        const string fileName = "libSkiaSharp.dll";
        const string resourceName = "PMGrapherUploader.libSkiaSharp.dll";
        string targetPath = Path.Combine(AppContext.BaseDirectory, fileName);

        if (File.Exists(targetPath) && new FileInfo(targetPath).Length > 1_000_000)
            return;

        using Stream? source = Assembly.GetExecutingAssembly().GetManifestResourceStream(resourceName);
        if (source is null)
            throw new InvalidOperationException("Embedded graph-rendering library is missing.");

        string temporaryPath = targetPath + ".new";
        using (var destination = new FileStream(temporaryPath, FileMode.Create, FileAccess.Write, FileShare.None))
            source.CopyTo(destination);

        File.Move(temporaryPath, targetPath, true);
    }

    private static void EnsureStartsWithWindows()
    {
        try
        {
            string startupDirectory = Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
                "Microsoft",
                "Windows",
                "Start Menu",
                "Programs",
                "Startup");
            Directory.CreateDirectory(startupDirectory);

            string executablePath = Environment.ProcessPath
                ?? Path.Combine(AppContext.BaseDirectory, "PMGrapherUploader.exe");
            string escapedPath = executablePath.Replace("%", "%%", StringComparison.Ordinal);
            string launcherPath = Path.Combine(startupDirectory, "PMGrapherUploader Auto Start.cmd");
            string launcherText =
                "@echo off\r\n" +
                $"start \"\" /min \"{escapedPath}\" --scheduled\r\n";

            if (!File.Exists(launcherPath) || File.ReadAllText(launcherPath) != launcherText)
                File.WriteAllText(launcherPath, launcherText);

            Console.WriteLine("Automatic start after Windows logon is enabled.");
        }
        catch (Exception ex)
        {
            Console.WriteLine("Warning: automatic Windows startup could not be enabled: " + ex.Message);
        }
    }

    private static string ResolveInputDirectory()
    {
        string? configured = Environment.GetEnvironmentVariable(InputEnvironmentVariable);
        if (!string.IsNullOrWhiteSpace(configured))
            return Path.GetFullPath(configured.Trim());

        const string originalInput = @"Z:\textfiles";
        return Directory.Exists(originalInput) ? originalInput : AppContext.BaseDirectory;
    }

    private static string ResolveOutputDirectory()
    {
        string? configured = Environment.GetEnvironmentVariable(OutputEnvironmentVariable);
        return string.IsNullOrWhiteSpace(configured)
            ? AppContext.BaseDirectory
            : Path.GetFullPath(configured.Trim());
    }

    private static async Task GenerateGraphsAndUpload(bool dryRun)
    {
        if (!Directory.Exists(InputDir))
            throw new DirectoryNotFoundException("Data directory was not found: " + InputDir);

        DateTime graphHour = await DetermineGraphHourUtc();
        Console.WriteLine($"Building rolling graph ending {graphHour:yyyy-MM-dd HH:00} UTC...");

        Samples.Clear();
        for (int i = 23; i >= 0; i--)
            await AddSampleForHour(graphHour.AddHours(-i));

        byte[] pm25Bytes = RenderGraph(Metric.PM25, graphHour.Year);
        byte[] pm10Bytes = RenderGraph(Metric.PM10, graphHour.Year);

        string out25 = Path.Combine(OutputDir, "pm25_24h.png");
        string out10 = Path.Combine(OutputDir, "pm10_24h.png");

        File.WriteAllBytes(out25, pm25Bytes);
        File.WriteAllBytes(out10, pm10Bytes);

        Console.WriteLine($"Generated {Samples.Count} hourly points:");
        Console.WriteLine(out25);
        Console.WriteLine(out10);

        ArchiveDailyGraphs(graphHour.Date);

        if (!dryRun)
        {
            Program.UploadBothFiles();
            Console.WriteLine("Both graphs uploaded.");
        }
    }

    private static async Task<DateTime> DetermineGraphHourUtc()
    {
        string? latestFile = Directory
            .EnumerateFiles(InputDir, DataFilePattern, SearchOption.TopDirectoryOnly)
            .OrderByDescending(Path.GetFileName)
            .FirstOrDefault();

        if (latestFile is null)
            throw new FileNotFoundException(
                $"No {DataFilePattern} file was found in {InputDir}.");

        List<Row> latestRows = await ReadRowsFromFile(latestFile);
        if (latestRows.Count == 0)
            throw new InvalidDataException("No valid PM rows were found in " + latestFile);

        DateTime latestTime = latestRows.Max(r => r.Time);
        DateTime currentHour = FloorToHour(DateTime.UtcNow);

        if (latestTime >= currentHour.AddHours(-1).AddMinutes(55))
        {
            Console.WriteLine($"Latest monitor data: {latestTime:yyyy-MM-dd HH:mm:ss} UTC.");
            return currentHour;
        }

        DateTime latestCompleteHour = FloorToHour(latestTime);
        Console.WriteLine($"Live data is stale; using latest data at {latestTime:yyyy-MM-dd HH:mm:ss} UTC.");
        return latestCompleteHour;
    }

    private static DateTime FloorToHour(DateTime time) =>
        new(time.Year, time.Month, time.Day, time.Hour, 0, 0, DateTimeKind.Utc);

    private static async Task AddSampleForHour(DateTime hour)
    {
        List<Row> rows = await ReadLast60RowsBefore(hour);
        Console.WriteLine($"{hour:yyyy-MM-dd HH:00} UTC: {rows.Count} rows");

        if (rows.Count == 0)
            return;

        Samples.Add(new Sample(
            hour,
            rows.Average(r => r.Pm25),
            rows.Average(r => r.Pm10)));
    }

    private static async Task<List<Row>> ReadLast60RowsBefore(DateTime hour)
    {
        string[] candidateFiles = new[] { hour, hour.AddHours(-1) }
            .Select(t => Path.Combine(InputDir, $"DUSTMONITOR_20746_{t:yyyy_MM}.txt"))
            .Distinct(StringComparer.OrdinalIgnoreCase)
            .Where(File.Exists)
            .ToArray();

        var rows = new List<Row>();
        foreach (string file in candidateFiles)
            rows.AddRange(await ReadRowsFromFile(file));

        return rows
            .Where(r => r.Time < hour)
            .OrderBy(r => r.Time)
            .TakeLast(60)
            .ToList();
    }

    private static async Task<List<Row>> ReadRowsFromFile(string file)
    {
        var rows = new List<Row>();
        using var fs = new FileStream(file, FileMode.Open, FileAccess.Read, FileShare.ReadWrite);
        long start = Math.Max(0, fs.Length - TailBytes);
        fs.Seek(start, SeekOrigin.Begin);

        using var reader = new StreamReader(fs);
        if (start > 0)
            await reader.ReadLineAsync();

        while (!reader.EndOfStream)
        {
            string? line = await reader.ReadLineAsync();
            if (string.IsNullOrWhiteSpace(line))
                continue;

            string[] columns = line.Split('\t');
            if (columns.Length < 7 || columns[0].StartsWith("date", StringComparison.OrdinalIgnoreCase))
                continue;

            if (!TryParseTimestamp(columns[0], columns[1], out DateTime timestamp))
                continue;
            if (!double.TryParse(columns[4], NumberStyles.Any, CultureInfo.InvariantCulture, out double pm25))
                continue;
            if (!double.TryParse(columns[6], NumberStyles.Any, CultureInfo.InvariantCulture, out double pm10))
                continue;

            rows.Add(new Row(timestamp, pm25, pm10));
        }

        return rows;
    }

    private static bool TryParseTimestamp(string date, string time, out DateTime timestamp) =>
        DateTime.TryParseExact(
            date + " " + time,
            new[]
            {
                "M/d/yyyy h:mm:ss tt",
                "MM/dd/yyyy h:mm:ss tt",
                "M/d/yyyy hh:mm:ss tt",
                "MM/dd/yyyy hh:mm:ss tt"
            },
            CultureInfo.InvariantCulture,
            DateTimeStyles.AssumeUniversal | DateTimeStyles.AdjustToUniversal,
            out timestamp);

    private static void ArchiveDailyGraphs(DateTime archiveDateUtc)
    {
        try
        {
            string current25 = Path.Combine(OutputDir, "pm25_24h.png");
            string current10 = Path.Combine(OutputDir, "pm10_24h.png");
            string dayStamp = archiveDateUtc.ToString("ddMMyyyy", CultureInfo.InvariantCulture);

            File.Copy(current25, Path.Combine(ArchiveDir, $"{dayStamp}_PM25.png"), true);
            File.Copy(current10, Path.Combine(ArchiveDir, $"{dayStamp}_PM10.png"), true);
        }
        catch (Exception ex)
        {
            Console.WriteLine("Archive warning: " + ex.Message);
        }
    }

    private static byte[] RenderGraph(Metric metric, int graphYear)
    {
        const int width = 1200;
        const int height = 450;
        const int padLeft = 125;
        const int padRight = 30;
        const int padTop = 40;
        const int padBottom = 140;

        using var surface = SKSurface.Create(new SKImageInfo(width, height));
        SKCanvas canvas = surface.Canvas;
        canvas.Clear(SKColors.White);

        using var axisPaint = new SKPaint
        {
            Color = SKColors.Black,
            StrokeWidth = 2,
            IsAntialias = true,
            Style = SKPaintStyle.Stroke
        };
        using var gridPaint = new SKPaint
        {
            Color = new SKColor(220, 220, 220),
            StrokeWidth = 1,
            IsAntialias = true
        };
        using var barPaint = new SKPaint
        {
            Color = metric == Metric.PM25 ? new SKColor(60, 150, 255) : new SKColor(70, 130, 180),
            IsAntialias = true,
            Style = SKPaintStyle.Fill
        };
        using var titlePaint = TextPaint(22, true);
        using var axisLabelPaint = TextPaint(19, true);
        using var yTickPaint = TextPaint(19, true);
        using var xTickLabelPaint = TextPaint(13, true);
        using var utcLabelPaint = TextPaint(19, true);

        int plotWidth = width - padLeft - padRight;
        int plotHeight = height - padTop - padBottom;
        float x0 = padLeft;
        float y0 = padTop + plotHeight;
        float x1 = padLeft + plotWidth;
        float y1 = padTop;

        List<Sample> ordered = Samples.OrderBy(s => s.Time).ToList();
        List<double> values = ordered
            .Select(s => metric == Metric.PM25 ? s.Pm25 : s.Pm10)
            .ToList();

        double max = values.Count > 0 ? values.Max() : 1;
        double step = max <= 30 ? 5.0 : 10.0;
        double yMax = Math.Max(step * 2, Math.Ceiling((max + 10.0) / step) * step);

        string title = metric == Metric.PM25 ? "PM 2.5" : "PM 10";
        float titleWidth = titlePaint.MeasureText(title);
        canvas.DrawText(title, padLeft + (plotWidth - titleWidth) / 2f, 28, titlePaint);
        canvas.DrawRect(new SKRect(x0, y1, x1, y0), axisPaint);

        int yTicks = Math.Max(1, (int)(yMax / step));
        for (int i = 0; i <= yTicks; i++)
        {
            double value = i * step;
            float y = MapY(value, 0, yMax, y1, y0);
            canvas.DrawLine(x0, y, x1, y, gridPaint);
            string tick = value.ToString("F0", CultureInfo.InvariantCulture);
            canvas.DrawText(tick, x0 - 10 - yTickPaint.MeasureText(tick), y + 6, yTickPaint);
        }

        const string yAxisLabel = "MASS CONCENTRATION (μg/m³)";
        float yAxisWidth = axisLabelPaint.MeasureText(yAxisLabel);
        canvas.Save();
        canvas.Translate(60, y1 + (plotHeight + yAxisWidth) / 2f);
        canvas.RotateDegrees(-90);
        canvas.DrawText(yAxisLabel, 0, 0, axisLabelPaint);
        canvas.Restore();

        if (ordered.Count == 0)
        {
            canvas.DrawText("No valid data", x0 + 200, y0 - 100, axisLabelPaint);
        }
        else
        {
            float slot = plotWidth / (float)ordered.Count;
            float barWidth = slot * 0.7f;
            float gap = slot - barWidth;

            for (int i = 0; i < ordered.Count; i++)
            {
                float left = x0 + i * slot + gap / 2f;
                float right = left + barWidth;
                float y = MapY(values[i], 0, yMax, y1, y0);
                canvas.DrawRect(new SKRect(left, y, right, y0), barPaint);

                string label = ordered[i].Time.ToString("dd.MM  HH:00", CultureInfo.InvariantCulture);
                float labelX = x0 + i * slot + slot / 2f;
                canvas.DrawLine(labelX, y0, labelX, y0 + 6, axisPaint);
                canvas.Save();
                canvas.Translate(labelX, y0 + 8);
                canvas.RotateDegrees(90);
                canvas.DrawText(label, 0, 0, xTickLabelPaint);
                canvas.Restore();
            }
        }

        string utcLabel = "DATE and TIME (UTC) in " + graphYear;
        float utcWidth = utcLabelPaint.MeasureText(utcLabel);
        canvas.DrawText(utcLabel, padLeft + (plotWidth - utcWidth) / 2f, height - 25, utcLabelPaint);

        using SKImage image = surface.Snapshot();
        using SKData data = image.Encode(SKEncodedImageFormat.Png, 100);
        return data.ToArray();
    }

    private static SKPaint TextPaint(float size, bool bold) => new()
    {
        Color = SKColors.Black,
        TextSize = size,
        FakeBoldText = bold,
        IsAntialias = true
    };

    private static float MapY(double value, double min, double max, float top, float bottom)
    {
        if (max <= min)
            return bottom;

        double ratio = Math.Clamp((value - min) / (max - min), 0, 1);
        return (float)(bottom - ratio * (bottom - top));
    }

    private static async Task WaitUntilNextHourUtc()
    {
        DateTime now = DateTime.UtcNow;
        DateTime next = FloorToHour(now).AddHours(1).AddMinutes(1);
        TimeSpan delay = next - now;
        if (delay < TimeSpan.Zero)
            delay = TimeSpan.Zero;

        Console.WriteLine($"Next graph will run at {next:yyyy-MM-dd HH:mm:ss} UTC.");
        await Task.Delay(delay);
    }

    private readonly record struct Row(DateTime Time, double Pm25, double Pm10);
    private readonly record struct Sample(DateTime Time, double Pm25, double Pm10);
    private enum Metric { PM25, PM10 }
}
