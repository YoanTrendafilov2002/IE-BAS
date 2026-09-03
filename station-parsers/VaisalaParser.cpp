#define NOMINMAX
#include <windows.h>
#include <commdlg.h>

#include <iostream>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>
#include <map>
#include <cctype>

using namespace std;

static vector<string> split_ws(const string& s) {
    vector<string> out;
    istringstream iss(s);
    string tok;
    while (iss >> tok) out.push_back(tok);
    return out;
}

static bool is_number(const string& s) {
    if (s.empty()) return false;
    size_t i = 0;
    if (s[i] == '+' || s[i] == '-') i++;
    bool digit = false, dot = false;
    for (; i < s.size(); i++) {
        if (isdigit((unsigned char)s[i])) digit = true;
        else if (s[i] == '.' && !dot) dot = true;
        else return false;
    }
    return digit;
}

static string json_escape(const string& s) {
    string o;
    o.reserve(s.size() + 8);
    for (char c : s) {
        switch (c) {
            case '\\': o += "\\\\"; break;
            case '"':  o += "\\\""; break;
            case '\n': o += "\\n"; break;
            case '\r': o += "\\r"; break;
            case '\t': o += "\\t"; break;
            default:   o += c; break;
        }
    }
    return o;
}

static void split_path(const string& full, string& dir, string& base, string& ext) {
    size_t slash = full.find_last_of("\\/");
    dir = (slash == string::npos) ? "" : full.substr(0, slash + 1);
    string name = (slash == string::npos) ? full : full.substr(slash + 1);

    size_t dot = name.find_last_of('.');
    if (dot == string::npos) {
        base = name;
        ext = "";
    } else {
        base = name.substr(0, dot);
        ext = name.substr(dot); // includes dot
    }
}

static bool pick_file_windows(string& outPath) {
    char fileName[MAX_PATH] = {0};

    OPENFILENAMEA ofn;
    ZeroMemory(&ofn, sizeof(ofn));
    ofn.lStructSize = sizeof(ofn);
    ofn.hwndOwner = nullptr;
    ofn.lpstrFile = fileName;
    ofn.nMaxFile = MAX_PATH;

    // Filter: Text/Log/All
    ofn.lpstrFilter =
        "Log/Text Files\0*.txt;*.log;*.csv;*.dat\0"
        "All Files\0*.*\0";
    ofn.nFilterIndex = 1;
    ofn.Flags = OFN_PATHMUSTEXIST | OFN_FILEMUSTEXIST;

    if (GetOpenFileNameA(&ofn)) {
        outPath = fileName;
        return true;
    }
    return false;
}

int main() {
    string inputPath;
    cout << "Vaisala WXT536 M22 -> JSONL exporter (standalone)\n";
    cout << "Pick a file...\n";

    if (!pick_file_windows(inputPath)) {
        cout << "No file selected. Exiting.\n";
        return 0;
    }

    ifstream in(inputPath);
    if (!in) {
        cerr << "ERROR: cannot open input file.\n";
        return 1;
    }

    string dir, base, ext;
    split_path(inputPath, dir, base, ext);

    // output next to input
    string outputPath = dir + base + "_vaisala.jsonl";

    ofstream out(outputPath);
    if (!out) {
        cerr << "ERROR: cannot create output file: " << outputPath << "\n";
        return 1;
    }

    // Expected field order:
    // R Wifi Dn Dm Dx Sn Sm Sx Ta Ua Pa Rc Rd Ri Hc Hd Hi Th Vh Vs Vr Unixtime
    const char* keys[] = {
        "R","Wifi","Dn","Dm","Dx","Sn","Sm","Sx","Ta","Ua","Pa",
        "Rc","Rd","Ri","Hc","Hd","Hi","Th","Vh","Vs","Vr","Unixtime"
    };

    string line;
    long long exported = 0;
    while (getline(in, line)) {
        if (line.find(" M22 ") == string::npos) continue;

        auto t = split_ws(line);

        // Find M22 token index
        int iM22 = -1;
        for (int i = 0; i < (int)t.size(); i++) {
            if (t[i] == "M22") { iM22 = i; break; }
        }
        if (iM22 < 0) continue;

        // Flattened input format:
        // G97 R M22 0 870 86 288 292 ...
        // M22 is followed by a status flag and then the data fields.
        int i = iM22 + 1;
        if (i >= (int)t.size()) continue;

        string flag = t[i++]; // usually 0
        (void)flag; // unused (kept if you want it later)

        // Need 22 fields + Unixtime at least
        const int need = 22; // R..Vr + Unixtime = 22 (we excluded datetime string)
        if (i + need > (int)t.size()) continue;

        map<string, string> rec;
        for (int k = 0; k < need; k++) {
            rec[keys[k]] = t[i++];
        }

        // optional human timestamp at end if present
        if (i < (int)t.size()) {
            rec["datetime"] = t[i];
        }

        // add identity info (useful downstream)
        rec["station"] = "Vaisala_WXT536";
        rec["format"]  = "vaisala_M22_flat";

        // write JSON object (JSONL)
        out << "{";
        bool first = true;
        for (const auto& kv : rec) {
            if (!first) out << ",";
            first = false;
            out << "\"" << json_escape(kv.first) << "\":";
            if (is_number(kv.second)) out << kv.second;
            else out << "\"" << json_escape(kv.second) << "\"";
        }
        out << "}\n";

        exported++;
    }

    cout << "\nDone.\n";
    cout << "Exported records: " << exported << "\n";
    cout << "Output: " << outputPath << "\n";
    return 0;
}
