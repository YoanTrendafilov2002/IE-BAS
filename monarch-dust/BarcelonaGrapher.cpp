// BarcelonaGrapher.cpp
// Windows-only, single-file.
// - Reads MONARCH daily JSON produced by your BarcelonaDust script (may contain NaN tokens)
// - Exports:
//    1) dust_load vs forecast_hour (0..72h only) -> CSV + PNG
//    2) sconc_dust heatmap (forecast_hour vs level_m, starting at 1000 m) -> CSV + PNG
// - Calls gnuplot to render plots
//
// Build (MSVC):  cl /std:c++17 /O2 BarcelonaGrapher.cpp
// Run:           BarcelonaGrapher.exe
//
// Requirements:
// - gnuplot installed and available in PATH (gnuplot.exe callable)

#include <iostream>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>
#include <map>
#include <filesystem>
#include <cstdlib>
#include <cctype>
#include <algorithm>
#include <stdexcept>
#include <cmath>

namespace fs = std::filesystem;

// ============================
// CONFIG (edit if needed)
// ============================
static const fs::path SRC_DIR = "output_json";
static const fs::path OUT_DIR = "DustGraphs";

// Only plot up to 72 hours
static constexpr double MAX_FORECAST_H = 72.0;

// Heatmap should start at 1000 m
static constexpr double HEAT_MIN_LEVEL_M = 1000.0;

// If value is missing/null (after NaN sanitization), emit 0 in heatmap
static constexpr bool HEAT_EMIT_ZERO_FOR_MISSING = true;

// ============================
// Minimal JSON parser (embedded)
// Supports: null, bool, number, string, array, object.
// ============================

namespace minijson {

    struct Value {
        enum Type { NUL, BOOL, NUMBER, STRING, ARRAY, OBJECT } type = NUL;

        bool b = false;
        double num = 0.0;
        std::string str;
        std::vector<Value> arr;
        std::map<std::string, Value> obj;

        bool is_null()   const { return type == NUL; }
        bool is_bool()   const { return type == BOOL; }
        bool is_number() const { return type == NUMBER; }
        bool is_string() const { return type == STRING; }
        bool is_array()  const { return type == ARRAY; }
        bool is_object() const { return type == OBJECT; }

        const Value& at(const std::string& key) const {
            static Value nullv;
            if (!is_object()) return nullv;
            auto it = obj.find(key);
            if (it == obj.end()) return nullv;
            return it->second;
        }
    };

    struct Parser {
        static void skip_ws(const char*& p) {
            while (*p && std::isspace(static_cast<unsigned char>(*p))) ++p;
        }

        static bool match(const char*& p, const char* lit) {
            const char* q = p;
            while (*lit) {
                if (*q != *lit) return false;
                ++q; ++lit;
            }
            p = q;
            return true;
        }

        static bool parse_string(const char*& p, std::string& out, std::string& err) {
            if (*p != '"') { err = "expected string '\"'"; return false; }
            ++p;
            std::string s;
            while (*p) {
                char c = *p++;
                if (c == '"') { out = s; return true; }
                if (c == '\\') {
                    char e = *p++;
                    switch (e) {
                    case '"': s.push_back('"'); break;
                    case '\\': s.push_back('\\'); break;
                    case '/': s.push_back('/'); break;
                    case 'b': s.push_back('\b'); break;
                    case 'f': s.push_back('\f'); break;
                    case 'n': s.push_back('\n'); break;
                    case 'r': s.push_back('\r'); break;
                    case 't': s.push_back('\t'); break;
                    case 'u': {
                        // minimal \u handling: read 4 hex digits, store as '?'
                        for (int i = 0; i < 4; i++) {
                            if (!std::isxdigit(static_cast<unsigned char>(p[i]))) { err = "bad \\u escape"; return false; }
                        }
                        p += 4;
                        s.push_back('?');
                    } break;
                    default:
                        err = "bad escape sequence";
                        return false;
                    }
                }
                else {
                    s.push_back(c);
                }
            }
            err = "unterminated string";
            return false;
        }

        static bool parse_number(const char*& p, double& out, std::string& err) {
            const char* start = p;
            if (*p == '-' || *p == '+') ++p;

            if (!std::isdigit(static_cast<unsigned char>(*p)) && *p != '.') {
                err = "bad number";
                return false;
            }

            while (std::isdigit(static_cast<unsigned char>(*p))) ++p;
            if (*p == '.') {
                ++p;
                while (std::isdigit(static_cast<unsigned char>(*p))) ++p;
            }
            if (*p == 'e' || *p == 'E') {
                ++p;
                if (*p == '-' || *p == '+') ++p;
                while (std::isdigit(static_cast<unsigned char>(*p))) ++p;
            }

            std::string token(start, p - start);
            try {
                out = std::stod(token);
                return true;
            }
            catch (...) {
                err = "stod failed";
                return false;
            }
        }

        static bool parse_array(const char*& p, Value& v, std::string& err) {
            if (*p != '[') { err = "expected '['"; return false; }
            ++p;
            skip_ws(p);

            v.type = Value::ARRAY;
            v.arr.clear();

            if (*p == ']') { ++p; return true; }

            while (*p) {
                Value elem;
                if (!parse_value(p, elem, err)) return false;
                v.arr.push_back(std::move(elem));

                skip_ws(p);
                if (*p == ',') { ++p; skip_ws(p); continue; }
                if (*p == ']') { ++p; return true; }
                err = "expected ',' or ']'";
                return false;
            }

            err = "unterminated array";
            return false;
        }

        static bool parse_object(const char*& p, Value& v, std::string& err) {
            if (*p != '{') { err = "expected '{'"; return false; }
            ++p;
            skip_ws(p);

            v.type = Value::OBJECT;
            v.obj.clear();

            if (*p == '}') { ++p; return true; }

            while (*p) {
                skip_ws(p);

                std::string key;
                if (!parse_string(p, key, err)) return false;

                skip_ws(p);
                if (*p != ':') { err = "expected ':'"; return false; }
                ++p;
                skip_ws(p);

                Value val;
                if (!parse_value(p, val, err)) return false;

                v.obj.emplace(std::move(key), std::move(val));

                skip_ws(p);
                if (*p == ',') { ++p; skip_ws(p); continue; }
                if (*p == '}') { ++p; return true; }
                err = "expected ',' or '}'";
                return false;
            }

            err = "unterminated object";
            return false;
        }

        static bool parse_value(const char*& p, Value& v, std::string& err) {
            skip_ws(p);
            if (!*p) { err = "unexpected end"; return false; }

            if (*p == '"') {
                v.type = Value::STRING;
                return parse_string(p, v.str, err);
            }
            if (*p == '{') return parse_object(p, v, err);
            if (*p == '[') return parse_array(p, v, err);

            if (match(p, "null")) { v.type = Value::NUL; return true; }
            if (match(p, "true")) { v.type = Value::BOOL; v.b = true; return true; }
            if (match(p, "false")) { v.type = Value::BOOL; v.b = false; return true; }

            v.type = Value::NUMBER;
            return parse_number(p, v.num, err);
        }

        static bool parse(const std::string& s, Value& out, std::string& err) {
            const char* p = s.c_str();
            if (!parse_value(p, out, err)) return false;
            skip_ws(p);
            if (*p != '\0') { err = "trailing garbage after JSON"; return false; }
            return true;
        }
    };

} // namespace minijson

// ============================
// Helpers
// ============================

static std::string read_text_file(const fs::path& p) {
    std::ifstream in(p, std::ios::binary);
    if (!in) throw std::runtime_error("cannot open file: " + p.string());
    std::ostringstream ss;
    ss << in.rdbuf();
    return ss.str();
}

// Replace NaN/Infinity tokens (not valid JSON) with null.
// Also handles common variants that appear in your file.
static void sanitize_non_json_numbers(std::string& s) {
    auto replace_all = [&](const std::string& a, const std::string& b) {
        size_t pos = 0;
        while ((pos = s.find(a, pos)) != std::string::npos) {
            s.replace(pos, a.size(), b);
            pos += b.size();
        }
        };

    // Most common in your JSON:  "250.0": NaN
    replace_all(": NaN", ": null");
    replace_all(":NaN", ":null");

    // Rare but safe
    replace_all(": Infinity", ": null");
    replace_all(":Infinity", ":null");
    replace_all(": -Infinity", ": null");
    replace_all(":-Infinity", ":null");
}

static void ensure_dir_or_throw(const fs::path& p) {
    std::error_code ec;
    fs::create_directories(p, ec);
    if (ec) throw std::runtime_error("failed to create directory: " + p.string());
}

static void write_text_file(const fs::path& p, const std::string& text) {
    std::ofstream out(p, std::ios::binary);
    if (!out) throw std::runtime_error("cannot write file: " + p.string());
    out << text;
}

static std::string gnuplot_path(const fs::path& p) {
    std::string s = p.string();
    std::replace(s.begin(), s.end(), '\\', '/'); // gnuplot happier with /
    return s;
}

static bool is_number(const minijson::Value& v) {
    return v.is_number();
}

static bool forecast_ok(const minijson::Value& fh) {
    return fh.is_number() && (fh.num >= 0.0) && (fh.num <= MAX_FORECAST_H + 1e-9);
}

// For gnuplot pm3d to work reliably with scattered triples, use:
// set pm3d map; set dgrid3d; splot ... with pm3d
static std::string make_heat_gnuplot(const fs::path& out_png, const fs::path& csv, const std::string& date) {
    std::ostringstream gp;
    gp << "set terminal pngcairo size 1400,800 font 'Consolas,12'\n";
    gp << "set output '" << gnuplot_path(out_png) << "'\n";
    gp << "set datafile separator ','\n";
    gp << "set title 'sconc_dust heatmap (time vs height) (" << date << ")'\n";
    gp << "set xlabel 'Forecast hour'\n";
    gp << "set ylabel 'Level (m)'\n";
    gp << "set grid\n";
    gp << "set view map\n";
    gp << "set pm3d map\n";
    gp << "set key off\n";
    gp << "set yrange [" << HEAT_MIN_LEVEL_M << ":*]\n";
    gp << "set ticslevel 0\n";

    // Make pm3d actually fill a surface from irregular (time,level,value) triples
    // Choose a grid matching your data: hours are 0,3,6..72 => 25 points
    // levels: 1000..12000 etc => about 11 points (depends)
    gp << "set dgrid3d 25,30\n";  // (xgrid,ygrid) - gives stable heatmaps
    gp << "set pm3d interpolate 1,1\n";
    gp << "set palette\n";

    // If you want log colors later, uncomment:
    // gp << "set logscale cb\n";

    gp << "splot '" << gnuplot_path(csv) << "' using 1:2:3 with pm3d\n";
    return gp.str();
}

static std::string make_dust_gnuplot(const fs::path& out_png, const fs::path& csv, const std::string& date) {
    std::ostringstream gp;
    gp << "set terminal pngcairo size 1400,800 font 'Consolas,12'\n";
    gp << "set output '" << gnuplot_path(out_png) << "'\n";
    gp << "set datafile separator ','\n";
    gp << "set title 'Dust load vs forecast hour (" << date << ")'\n";
    gp << "set xlabel 'Forecast hour'\n";
    gp << "set ylabel 'dust_load (kg m^{-2})'\n";
    gp << "set grid\n";
    gp << "set xrange [0:" << MAX_FORECAST_H << "]\n";
    gp << "plot '" << gnuplot_path(csv) << "' using 1:2 with lines lw 2 title 'dust_load'\n";
    return gp.str();
}

// ============================
// Main
// ============================

int main() {
    try {
        ensure_dir_or_throw(OUT_DIR);

        std::string date;
        std::cout << "Enter date (YYYY_MM_DD): ";
        std::cin >> date;

        const fs::path in_json = SRC_DIR / (date + "_00UTC.json");
        if (!fs::exists(in_json)) {
            std::cerr << "Input JSON not found: " << in_json.string() << "\n";
            return 1;
        }

        std::string txt = read_text_file(in_json);
        sanitize_non_json_numbers(txt);

        minijson::Value root;
        std::string err;
        if (!minijson::Parser::parse(txt, root, err)) {
            std::cerr << "JSON parse error: " << err << "\n";
            return 1;
        }
        if (!root.is_object()) {
            std::cerr << "Root is not an object.\n";
            return 1;
        }

        const auto& data = root.at("data");
        if (!data.is_array()) {
            std::cerr << "Missing or invalid root.data array.\n";
            return 1;
        }

        // --- Export dust_load timeseries CSV (0..72h) ---
        fs::path dust_csv = OUT_DIR / (date + "_dust_load.csv");
        int dust_n_ok = 0;
        {
            std::ostringstream ss;
            ss << "forecast_hour,dust_load_kg_m2\n";

            for (const auto& rec : data.arr) {
                if (!rec.is_object()) continue;

                const auto& fh = rec.at("forecast_hour");
                const auto& vars = rec.at("vars");
                if (!forecast_ok(fh) || !vars.is_object()) continue;

                const auto& dust_load = vars.at("dust_load");
                const auto& val = dust_load.at("value");
                if (!is_number(val)) continue;

                ss << fh.num << "," << val.num << "\n";
                ++dust_n_ok;
            }

            write_text_file(dust_csv, ss.str());
        }
        if (dust_n_ok == 0) {
            std::cerr << "Warning: dust_load CSV has 0 valid points in 0..72h.\n";
        }

        // --- Export sconc heatmap CSV (0..72h, level >= 1000 m) ---
        fs::path heat_csv = OUT_DIR / (date + "_sconc_heat.csv");
        int heat_n_ok = 0;
        {
            std::ostringstream ss;
            ss << "forecast_hour,level_m,sconc\n";

            for (const auto& rec : data.arr) {
                if (!rec.is_object()) continue;

                const auto& fh = rec.at("forecast_hour");
                const auto& vars = rec.at("vars");
                if (!forecast_ok(fh) || !vars.is_object()) continue;

                const auto& sconc = vars.at("sconc_dust");
                const auto& by_level = sconc.at("by_level_m");
                if (!by_level.is_object()) continue;

                for (const auto& kv : by_level.obj) {
                    const std::string& level_str = kv.first;
                    const minijson::Value& v = kv.second;

                    double level_m = 0.0;
                    try { level_m = std::stod(level_str); }
                    catch (...) { continue; }

                    // Start heatmap at 1000 m
                    if (level_m < HEAT_MIN_LEVEL_M) continue;

                    // Missing values -> emit 0 if requested
                    double val = 0.0;
                    if (v.is_number()) val = v.num;
                    else if (!HEAT_EMIT_ZERO_FOR_MISSING) continue;

                    ss << fh.num << "," << level_m << "," << val << "\n";
                    ++heat_n_ok;
                }
            }

            write_text_file(heat_csv, ss.str());
        }
        if (heat_n_ok == 0) {
            std::cerr << "Warning: sconc heat CSV has 0 valid points (>=1000m, 0..72h).\n";
        }

        // --- gnuplot scripts ---
        fs::path dust_gp = OUT_DIR / (date + "_dust_load.gnuplot");
        fs::path dust_png = OUT_DIR / (date + "_dust_load.png");
        write_text_file(dust_gp, make_dust_gnuplot(dust_png, dust_csv, date));

        fs::path heat_gp = OUT_DIR / (date + "_sconc_heat.gnuplot");
        fs::path heat_png = OUT_DIR / (date + "_sconc_heat.png");
        write_text_file(heat_gp, make_heat_gnuplot(heat_png, heat_csv, date));

        // Run gnuplot
        {
            std::string cmd1 = "gnuplot \"" + dust_gp.string() + "\"";
            std::string cmd2 = "gnuplot \"" + heat_gp.string() + "\"";

            int r1 = std::system(cmd1.c_str());
            if (r1 != 0) {
                std::cerr << "gnuplot failed for dust_load.\nCommand:\n" << cmd1 << "\n";
                return 1;
            }
            int r2 = std::system(cmd2.c_str());
            if (r2 != 0) {
                std::cerr << "gnuplot failed for sconc heatmap.\nCommand:\n" << cmd2 << "\n";
                return 1;
            }
        }

        std::cout << "Wrote:\n  " << dust_csv.string() << "\n  " << dust_png.string()
            << "\n  " << heat_csv.string() << "\n  " << heat_png.string() << "\n";
        return 0;

    }
    catch (const std::exception& e) {
        std::cerr << "Fatal: " << e.what() << "\n";
        return 1;
    }
}
