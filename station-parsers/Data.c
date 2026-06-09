#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>

#define LINE_BUF 4096
#define PATH_BUF 1024

/*
 M0 payload order (WSx-UMB terminal mode):
 0  Air temperature (°C)
 3  Relative humidity (%)
 4  Relative air pressure (hPa)
 5  Wind speed (m/s)
 6  Wind direction (deg)
*/

static const char* find_token(const char* s, const char* token)
{
    size_t len = strlen(token);
    for (const char* p = s; *p; ++p) {
        if ((p == s || isspace((unsigned char)p[-1])) &&
            strncmp(p, token, len) == 0 &&
            (p[len] == '\0' || isspace((unsigned char)p[len]))) {
            return p;
        }
    }
    return NULL;
}

static int parse_m0(const char* line,
                    double* tempC,
                    double* rh,
                    double* pressure,
                    double* windSpeed,
                    double* windDir)
{
    const char* m0 = find_token(line, "M0");
    if (!m0) return 0;

    const char* p = m0 + 2;
    double v[10];

    for (int i = 0; i < 10; ++i) {
        while (*p && isspace((unsigned char)*p)) p++;
        if (!*p) return 0;

        char* end;
        v[i] = strtod(p, &end);
        if (end == p) return 0;
        p = end;
    }

    *tempC     = v[0];
    *rh        = v[3];
    *pressure  = v[4];
    *windSpeed = v[5];
    *windDir   = v[6];
    return 1;
}

/* Extract filename without extension */
static void extract_basename(const char* path, char* out, size_t outSize)
{
    const char* name = path;
    const char* p = path;

    while (*p) {
        if (*p == '\\' || *p == '/')
            name = p + 1;
        p++;
    }

    strncpy(out, name, outSize - 1);
    out[outSize - 1] = '\0';

    char* dot = strrchr(out, '.');
    if (dot) *dot = '\0';
}

int main(void)
{
    char inPath[PATH_BUF];
    char baseName[PATH_BUF];
    char outPath[PATH_BUF];

    printf("Enter INPUT file path:\n> ");
    if (!fgets(inPath, sizeof(inPath), stdin)) {
        fprintf(stderr, "Input error.\n");
        return 1;
    }
    inPath[strcspn(inPath, "\r\n")] = 0;

    extract_basename(inPath, baseName, sizeof(baseName));

    snprintf(outPath, sizeof(outPath), "%s.json", baseName);

    FILE* in = fopen(inPath, "rb");
    if (!in) {
        fprintf(stderr, "Cannot open input file:\n%s\n", inPath);
        return 1;
    }

    FILE* out = fopen(outPath, "wb");
    if (!out) {
        fclose(in);
        fprintf(stderr, "Cannot create output file:\n%s\n", outPath);
        fprintf(stderr, "Make sure the directory exists.\n");
        return 1;
    }

    fputs("[\n", out);

    char line[LINE_BUF];
    int first = 1;
    int records = 0;

    while (fgets(line, sizeof(line), in)) {
        double t, rh, p, ws, wd;
        if (!parse_m0(line, &t, &rh, &p, &ws, &wd))
            continue;

        if (!first) fputs(",\n", out);
        first = 0;

        fprintf(out,
            "  {\"temp_c\":%.3f,\"rh_percent\":%.3f,"
            "\"pressure_hpa\":%.3f,\"wind_speed_ms\":%.3f,"
            "\"wind_dir_deg\":%.3f}",
            t, rh, p, ws, wd);

        records++;
    }

    fputs("\n]\n", out);

    fclose(in);
    fclose(out);

    printf("\nDone.\nParsed %d records.\nSaved to:\n%s\n",
           records, outPath);

    return 0;
}
