using System;
using System.IO;
using System.Linq;
using System.Threading;
using FluentFTP;

internal static class Program
{
    private static readonly string LocalDir =
        Environment.GetEnvironmentVariable("FTPPM_LOCAL_DIR")
        ?? AppContext.BaseDirectory;

    private static readonly string FtpHost = System.Environment.GetEnvironmentVariable("FTP_HOST")
        ?? throw new System.InvalidOperationException("Set FTP_HOST before running.");
    private static readonly string FtpUser = System.Environment.GetEnvironmentVariable("FTP_USER")
        ?? throw new System.InvalidOperationException("Set FTP_USER before running.");
    private static readonly string FtpPassword = System.Environment.GetEnvironmentVariable("FTP_PASSWORD")
        ?? throw new System.InvalidOperationException("Set FTP_PASSWORD before running.");
    private static readonly string RemoteDir = "/";  // change if needed

    private static readonly TimeSpan PollInterval = TimeSpan.FromSeconds(15);
    private static readonly TimeSpan FileSettleDelay = TimeSpan.FromSeconds(5);
    private static readonly TimeSpan RetryInterval = TimeSpan.FromMinutes(1);
    private static readonly string LogPath = Path.Combine(LocalDir, "ftp-uploader.log");
    private static readonly string LockPath = Path.Combine(LocalDir, ".ftp-uploader.lock");
    private static readonly object LogSync = new();

    private sealed record FileState(long Length, DateTime LastWriteTimeUtc);
    private sealed record UploadState(FileState Pm25, FileState Pm10)
    {
        public DateTime LatestWriteTimeUtc =>
            Pm25.LastWriteTimeUtc > Pm10.LastWriteTimeUtc
                ? Pm25.LastWriteTimeUtc
                : Pm10.LastWriteTimeUtc;
    }

    private static int Main(string[] args)
    {
        Directory.CreateDirectory(LocalDir);

        FileStream instanceLock;
        try
        {
            instanceLock = new FileStream(
                LockPath,
                FileMode.OpenOrCreate,
                FileAccess.ReadWrite,
                FileShare.None);
        }
        catch (IOException)
        {
            Log("Another uploader instance is already running; exiting.");
            return 0;
        }

        using (instanceLock)
        using (var shutdown = new CancellationTokenSource())
        {
            Console.CancelKeyPress += (_, eventArgs) =>
            {
                eventArgs.Cancel = true;
                shutdown.Cancel();
            };

            bool dryRun = args.Any(arg =>
                string.Equals(arg, "--dry-run", StringComparison.OrdinalIgnoreCase));
            bool runOnce = dryRun || args.Any(arg =>
                string.Equals(arg, "--once", StringComparison.OrdinalIgnoreCase));
            UploadState? lastUploadedState = null;
            DateTime retryAfterUtc = DateTime.MinValue;
            string? lastWaitingMessage = null;

            Log(runOnce
                ? "Self-contained uploader started in one-shot mode."
                : "Self-contained uploader started; monitoring PM charts.");

            while (!shutdown.IsCancellationRequested)
            {
                try
                {
                    UploadState currentState = ReadUploadState();
                    if (lastUploadedState == currentState)
                    {
                        lastWaitingMessage = null;
                        if (runOnce)
                            return 0;

                        Wait(shutdown.Token, PollInterval);
                        continue;
                    }

                    TimeSpan age = DateTime.UtcNow - currentState.LatestWriteTimeUtc;
                    if (age < FileSettleDelay)
                    {
                        LogWaitingOnce(
                            ref lastWaitingMessage,
                            "PM chart update detected; waiting for both files to settle.");
                        Wait(shutdown.Token, FileSettleDelay - age);
                        continue;
                    }

                    if (DateTime.UtcNow < retryAfterUtc)
                    {
                        Wait(shutdown.Token, retryAfterUtc - DateTime.UtcNow);
                        continue;
                    }

                    if (dryRun)
                    {
                        Log("Dry-run validation passed; both PM charts are ready for upload.");
                        return 0;
                    }

                    Log("New or changed PM charts detected; starting FTP upload.");
                    UploadBothFiles();
                    lastUploadedState = currentState;
                    retryAfterUtc = DateTime.MinValue;
                    lastWaitingMessage = null;
                    Log("FTP upload completed for both PM charts.");

                    if (runOnce)
                        return 0;
                }
                catch (Exception ex)
                {
                    Log("ERROR: " + ex.Message);
                    if (runOnce)
                        return 1;

                    retryAfterUtc = DateTime.UtcNow + RetryInterval;
                }

                Wait(shutdown.Token, PollInterval);
            }

            Log("Uploader stopped.");
            return 0;
        }
    }

    private static UploadState ReadUploadState()
    {
        return new UploadState(
            ReadFileState(Path.Combine(LocalDir, "pm25_24h.png")),
            ReadFileState(Path.Combine(LocalDir, "pm10_24h.png")));
    }

    private static FileState ReadFileState(string path)
    {
        if (!File.Exists(path))
            throw new FileNotFoundException("Missing local file.", path);

        var file = new FileInfo(path);
        return new FileState(file.Length, file.LastWriteTimeUtc);
    }

    internal static void UploadBothFiles()
    {
        using var client = new FtpClient(FtpHost, FtpUser, FtpPassword);
        client.Config.ConnectTimeout = 15_000;
        client.Config.ReadTimeout = 30_000;
        client.Config.DataConnectionConnectTimeout = 15_000;
        client.Config.DataConnectionReadTimeout = 30_000;
        client.Config.DataConnectionType = FtpDataConnectionType.AutoPassive;

        client.Connect();

        if (!string.IsNullOrWhiteSpace(RemoteDir) && RemoteDir != "/")
            client.CreateDirectory(RemoteDir);

        UploadFile(client, "pm25_24h.png");
        UploadFile(client, "pm10_24h.png");
        client.Disconnect();
    }

    private static void UploadFile(FtpClient client, string fileName)
    {
        string localPath = Path.Combine(LocalDir, fileName);
        string remotePath = CombineFtpPath(RemoteDir, fileName);
        FtpStatus status = client.UploadFile(
            localPath,
            remotePath,
            FtpRemoteExists.Overwrite);

        if (status != FtpStatus.Success)
        {
            throw new IOException(
                $"FTP server did not confirm upload of {fileName} (status: {status}).");
        }

        Log("Uploaded: " + remotePath);
    }

    private static void Wait(CancellationToken token, TimeSpan delay)
    {
        if (delay <= TimeSpan.Zero)
            return;

        token.WaitHandle.WaitOne(delay);
    }

    private static void LogWaitingOnce(ref string? previousMessage, string message)
    {
        if (string.Equals(previousMessage, message, StringComparison.Ordinal))
            return;

        previousMessage = message;
        Log(message);
    }

    private static void Log(string message)
    {
        string line = $"[{DateTime.Now:yyyy-MM-dd HH:mm:ss}] {message}";
        lock (LogSync)
        {
            try
            {
                RotateLogIfNeeded();
                File.AppendAllText(LogPath, line + Environment.NewLine);
            }
            catch
            {
                // Keep retrying uploads even if the diagnostic log is unavailable.
            }
        }

        Console.WriteLine(line);
    }

    private static void RotateLogIfNeeded()
    {
        const long maxLogSize = 5 * 1024 * 1024;
        if (!File.Exists(LogPath) || new FileInfo(LogPath).Length < maxLogSize)
            return;

        string previousLogPath = LogPath + ".1";
        File.Move(LogPath, previousLogPath, true);
    }

    private static string CombineFtpPath(string dir, string file)
    {
        dir = string.IsNullOrWhiteSpace(dir) ? "/" : dir.Replace('\\', '/');
        if (!dir.StartsWith("/")) dir = "/" + dir;
        if (dir.EndsWith("/")) return dir + file;
        return dir + "/" + file;
    }
}
