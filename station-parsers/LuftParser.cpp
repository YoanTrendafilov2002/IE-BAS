#include <algorithm>
#include <cctype>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <unordered_map>
#include <vector>

namespace fs = std::filesystem;

// Parsing helpers
static inline std::string trim(std::string s) {
    auto notSpace = [](unsigned char c){ return !std::isspace(c); };
    s.erase(s.begin(), std::find_if(s.begin(), s.end(), notSpace));
    s.erase(std::find_if(s.rbegin(), s.rend(), notSpace).base(), s.end());
    return s;
}

static inline std::vector<std::string> split_ws(const std::string& line) {
    std::istringstream iss(line);
    std::vector<std::string> out;
    std::string tok;
    while (iss >> tok) out.push_back(tok);
    return out;
}

static inline bool is_number_like(const std::string& s) {
    if (s.empty()) return false;
    size_t i = 0;
    if (s[i] == '+' || s[i] == '-') i++;
    bool anyDigit = false;
    bool dot = false;
    for (; i < s.size(); i++) {
        if (std::isdigit((unsigned char)s[i])) { anyDigit = true; continue; }
        if (s[i] == '.' && !dot) { dot = true; continue; }
        return false;
    }
    return anyDigit;
}

static inline std::string json_escape(const std::string& s) {
    std::string o;
    o.reserve(s.size() + 8);
    for (char c : s) {
        switch (c) {
            case '\\': o += "\\\\"; break;
            case '"':  o += "\\\""; break;
            case '\n': o += "\\n";  break;
            case '\r': o += "\\r";  break;
            case '\t': o += "\\t";  break;
            default:   o += c;      break;
        }
    }
    return o;
}

static inline std::string basename_noext(const std::string& path) {
    fs::path p(path);
    auto stem = p.stem().string();
    return stem.empty() ? "output" : stem;
}

// Vaisala format
static std::unordered_map<std::string, std::string>
parse_key_value_payload(const std::string& payload) {
    std::unordered_map<std::string, std::string> kv;

    std::stringstream ss(payload);
    std::string part;
    while (std::getline(ss, part, ',')) {
        part = trim(part);
        if (part.size() >= 2 && part[0] == '0' && (part[1] == 'R' || part[1] == 'r'))
            continue;

        auto eq = part.find('=');
        if (eq == std::string::npos) continue;

        std::string key = trim(part.substr(0, eq));
        std::string val = trim(part.substr(eq + 1));
        if (!key.empty())
            kv[key] = val;
    }
    return kv;
}

// Numeric order mapping (with Seq included after R):
// R Seq Wifi Dn Dm Dx Sn Sm Sx Ta Ua Pa Rc Rd Ri Hc Hd Hi Th Vh Vs Vr
static bool parse_vaisala_numeric_line(
    const std::vector<std::string>& t,
    std::unordered_map<std::string, std::string>& out,
    std::string& unixtime,
    std::string& dt
) {
    if (t.size() < 8) return false;

    if (t.size() >= 2 && is_number_like(t[t.size()-2])) {
        unixtime = t[t.size()-2];
        dt = t[t.size()-1];
    }

    int m22 = -1;
    for (int i = 0; i < (int)t.size(); i++) {
        if (t[i] == "M22") { m22 = i; break; }
    }
    if (m22 < 0) return false;

    int end = (int)t.size();
    if (!unixtime.empty()) end -= 2;

    std::vector<std::string> nums;
    for (int i = m22 + 1; i < end; i++) nums.push_back(t[i]);

    if ((int)nums.size() < 22) return false;

    out["R"]    = nums[0];
    out["Seq"]  = nums[1];
    out["Wifi"] = nums[2];

    out["Dn"] = nums[3];
    out["Dm"] = nums[4];
    out["Dx"] = nums[5];

    out["Sn"] = nums[6];
    out["Sm"] = nums[7];
    out["Sx"] = nums[8];

    out["Ta"] = nums[9];
    out["Ua"] = nums[10];
    out["Pa"] = nums[11];

    out["Rc"] = nums[12];
    out["Rd"] = nums[13];
    out["Ri"] = nums[14];

    out["Hc"] = nums[15];
    out["Hd"] = nums[16];
    out["Hi"] = nums[17];

    out["Th"] = nums[18];
    out["Vh"] = nums[19];
    out["Vs"] = nums[20];
    out["Vr"] = nums[21];

    return true;
}

// Luft format
static bool parse_luft_line(
    const std::vector<std::string>& t,
    std::unordered_map<std::string, std::string>& out,
    std::string& unixtime,
    std::string& dt
) {
    if (t.size() < 6) return false;

    if (t.size() >= 2 && is_number_like(t[t.size()-2])) {
        unixtime = t[t.size()-2];
        dt = t[t.size()-1];
    }

    if (!t.empty()) out["MsgType"] = t[0]; // e.g. G97

    // Check the station markers used by known sample files.
    for (const auto& tok : t) {
        if (tok == "NIT1" || tok == "WS500") {
            out["Station"] = tok;
            break;
        }
    }

    // If there is a token like R250
    for (const auto& tok : t) {
        if (tok.size() >= 2 && tok[0] == 'R' && is_number_like(tok.substr(1))) {
            out["R"] = tok.substr(1);
            break;
        }
    }

    for (const auto& tok : t) {
        if (tok.size() == 3 && tok[0] == 'M' &&
            std::isdigit((unsigned char)tok[1]) && std::isdigit((unsigned char)tok[2])) {
            out["M"] = tok;
            break;
        }
    }

    return true;
}

static std::string to_json_object(
    const std::string& mode_for_json,
    const std::string& product,
    const std::unordered_map<std::string, std::string>& fields,
    const std::string& unixtime,
    const std::string& dt,
    const std::string& raw_line
) {
    std::ostringstream o;
    o << "{";

    o << "\"mode\":\"" << json_escape(mode_for_json) << "\"";
    if (!product.empty()) o << ",\"product\":\"" << json_escape(product) << "\"";

    if (!unixtime.empty()) o << ",\"unixtime\":" << unixtime;
    if (!dt.empty()) o << ",\"datetime\":\"" << json_escape(dt) << "\"";

    o << ",\"data\":{";
    bool first = true;
    for (const auto& kv : fields) {
        if (!first) o << ",";
        first = false;
        o << "\"" << json_escape(kv.first) << "\":";
        if (is_number_like(kv.second)) o << kv.second;
        else o << "\"" << json_escape(kv.second) << "\"";
    }
    o << "}";

    o << ",\"raw\":\"" << json_escape(raw_line) << "\"";
    o << "}";
    return o.str();
}

static void pause_exit() {
    std::cout << "\nPress Enter to exit...";
    std::cout.flush();
    std::string dummy;
    std::getline(std::cin, dummy);
}

int main() {
    std::ios::sync_with_stdio(false);
    std::cin.tie(nullptr);

    // Prompt until a supported mode is selected.
    std::string mode_in;
    while (true) {
        std::cout << "Type mode (luft or vaisala): " << std::flush;
        if (!std::getline(std::cin, mode_in)) {
            std::cerr << "Error: could not read input.\n";
            pause_exit();
            return 1;
        }
        mode_in = trim(mode_in);
        std::string mode_lower = mode_in;
        std::transform(mode_lower.begin(), mode_lower.end(), mode_lower.begin(),
                       [](unsigned char c){ return (char)std::tolower(c); });

        if (mode_lower == "luft") { mode_in = "luft"; break; }
        if (mode_lower == "vaisala") { mode_in = "vaisala"; break; }
        if (mode_lower == "veisala") { mode_in = "vaisala"; break; } // accept typo, but force filename suffix = vaisala

        std::cout << "Invalid. Please type exactly: luft OR vaisala\n";
    }

    // Numeric mode used by the parser.
    const bool is_luft = (mode_in == "luft");
    const std::string mode_for_filename = mode_in;          // exactly "luft" or "vaisala"
    const std::string mode_for_json = mode_in;              // same (keeps consistent)
    const std::string product = is_luft ? "" : "Vaisala WXT536";

    // Read the input path.
    std::string inPath;
    std::cout << "Input file path: " << std::flush;
    if (!std::getline(std::cin, inPath)) {
        std::cerr << "Error: could not read input path.\n";
        pause_exit();
        return 1;
    }
    inPath = trim(inPath);

    std::ifstream fin(inPath);
    if (!fin) {
        std::cerr << "Error: cannot open input file: " << inPath << "\n";
        pause_exit();
        return 1;
    }

    const std::string base = basename_noext(inPath);
    const fs::path inputPath(inPath);
    const fs::path outPath =
        inputPath.parent_path() / (base + "_" + mode_for_filename + ".jsonl");

    std::ofstream fout(outPath);
    if (!fout) {
        std::cerr << "Error: cannot write output file: " << outPath << "\n";
        pause_exit();
        return 1;
    }

    std::string line;
    size_t ok = 0, fallback = 0;

    while (std::getline(fin, line)) {
        line = trim(line);
        if (line.empty()) continue;

        auto t = split_ws(line);
        if (t.empty()) continue;

        std::unordered_map<std::string, std::string> fields;
        std::string unixtime, dt;
        bool parsed = false;

        if (is_luft) {
            parsed = parse_luft_line(t, fields, unixtime, dt);
        } else {
            // Detect key=value payload
            bool hasKV = (line.find("Dn=") != std::string::npos) || (line.find("Ta=") != std::string::npos) ||
                         (line.find("Ua=") != std::string::npos) || (line.find("Pa=") != std::string::npos) ||
                         (line.find("Rc=") != std::string::npos);

            if (hasKV) {
                if (t.size() >= 2 && is_number_like(t[t.size()-2])) {
                    unixtime = t[t.size()-2];
                    dt = t[t.size()-1];
                }

                size_t startTok = 0;
                for (size_t i = 0; i < t.size(); i++) {
                    if (t[i].find("0R1") != std::string::npos || t[i].find("Dn=") != std::string::npos) {
                        startTok = i;
                        break;
                    }
                }

                std::string payload;
                for (size_t i = startTok; i < t.size(); i++) {
                    if (!unixtime.empty() && (i + 2 == t.size())) break; // stop before unixtime+dt
                    payload += t[i];
                }

                // remove spaces (payload is comma separated)
                payload.erase(std::remove(payload.begin(), payload.end(), ' '), payload.end());

                fields = parse_key_value_payload(payload);
                parsed = !fields.empty();
            } else {
                parsed = parse_vaisala_numeric_line(t, fields, unixtime, dt);
            }
        }

        if (!parsed) {
            fields.clear();
            fields["parse_error"] = "1";
            fallback++;
        } else {
            ok++;
        }

        fout << to_json_object(mode_for_json, product, fields, unixtime, dt, line) << "\n";
    }

    std::cout << "\nDone.\n"
              << "Output: " << outPath << "\n"
              << "Parsed: " << ok << "\n"
              << "Fallback: " << fallback << "\n";

    pause_exit();
    return 0;
}
