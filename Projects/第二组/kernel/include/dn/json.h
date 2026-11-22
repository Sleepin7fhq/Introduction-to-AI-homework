// ============================================================================
//  dn/json.h —— 极简 JSON 读写（仅供内核 IPC 使用，无第三方依赖）
//
//  目的：内核与 UI 之间只传结构化结果（类别/置信度/时长/告警），
//        不传任何音频数据。这里实现一个够用且无依赖的 JSON 解析/序列化。
// ============================================================================
#pragma once

#include <cctype>
#include <cmath>
#include <cstdio>
#include <map>
#include <memory>
#include <sstream>
#include <string>
#include <vector>

namespace dn {
namespace json {

class Value;
using Array = std::vector<Value>;
using Object = std::map<std::string, Value>;

enum class Type { Null, Bool, Number, String, Array, Object };

class Value {
 public:
  Value() : type_(Type::Null) {}
  Value(bool b) : type_(Type::Bool), bool_(b) {}
  Value(double d) : type_(Type::Number), num_(d) {}
  Value(int i) : type_(Type::Number), num_(static_cast<double>(i)) {}
  Value(long long i) : type_(Type::Number), num_(static_cast<double>(i)) {}
  Value(size_t i) : type_(Type::Number), num_(static_cast<double>(i)) {}
  Value(unsigned i) : type_(Type::Number), num_(static_cast<double>(i)) {}
  Value(const char* s) : type_(Type::String), str_(s ? s : "") {}
  Value(const std::string& s) : type_(Type::String), str_(s) {}
  Value(Array a) : type_(Type::Array), arr_(std::move(a)) {}
  Value(Object o) : type_(Type::Object), obj_(std::move(o)) {}

  Type type() const { return type_; }
  bool is_null() const { return type_ == Type::Null; }

  bool as_bool(bool def = false) const { return type_ == Type::Bool ? bool_ : def; }
  double as_number(double def = 0.0) const { return type_ == Type::Number ? num_ : def; }
  std::string as_string(const std::string& def = "") const {
    return type_ == Type::String ? str_ : def;
  }
  const Array& as_array() const { return arr_; }
  const Object& as_object() const { return obj_; }

  // 取子对象；不存在返回 nullptr
  const Value* find(const std::string& key) const {
    if (type_ != Type::Object) return nullptr;
    auto it = obj_.find(key);
    return it == obj_.end() ? nullptr : &it->second;
  }

  // ---- 解析 -------------------------------------------------------------
  static bool Parse(const std::string& text, Value* out, std::string* error) {
    size_t pos = 0;
    Value v;
    if (!ParseValue(text, pos, &v, error)) return false;
    SkipWs(text, pos);
    if (pos != text.size()) {
      if (error) *error = "JSON 末尾有多余字符";
      return false;
    }
    *out = std::move(v);
    return true;
  }

 private:
  static void SkipWs(const std::string& s, size_t& p) {
    while (p < s.size() && (s[p] == ' ' || s[p] == '\t' || s[p] == '\n' || s[p] == '\r')) ++p;
  }

  static bool ParseValue(const std::string& s, size_t& p, Value* out, std::string* err) {
    SkipWs(s, p);
    if (p >= s.size()) {
      if (err) *err = "JSON 内容为空";
      return false;
    }
    char c = s[p];
    if (c == '{') return ParseObject(s, p, out, err);
    if (c == '[') return ParseArray(s, p, out, err);
    if (c == '"') {
      std::string str;
      if (!ParseString(s, p, &str, err)) return false;
      *out = Value(str);
      return true;
    }
    if (s.compare(p, 4, "true") == 0) { p += 4; *out = Value(true); return true; }
    if (s.compare(p, 5, "false") == 0) { p += 5; *out = Value(false); return true; }
    if (s.compare(p, 4, "null") == 0) { p += 4; *out = Value(); return true; }
    // number
    size_t start = p;
    if (p < s.size() && (s[p] == '-' || s[p] == '+')) ++p;
    bool any = false;
    while (p < s.size() && (std::isdigit(static_cast<unsigned char>(s[p])) || s[p] == '.' ||
                            s[p] == 'e' || s[p] == 'E' || s[p] == '-' || s[p] == '+')) {
      if (std::isdigit(static_cast<unsigned char>(s[p]))) any = true;
      ++p;
    }
    if (!any) {
      if (err) *err = "无法解析的 JSON 记号";
      return false;
    }
    try {
      *out = Value(std::stod(s.substr(start, p - start)));
    } catch (...) {
      if (err) *err = "数字解析失败";
      return false;
    }
    return true;
  }

  static bool ParseString(const std::string& s, size_t& p, std::string* out, std::string* err) {
    if (p >= s.size() || s[p] != '"') {
      if (err) *err = "期望字符串";
      return false;
    }
    ++p;
    out->clear();
    while (p < s.size()) {
      char c = s[p++];
      if (c == '"') return true;
      if (c == '\\') {
        if (p >= s.size()) break;
        char e = s[p++];
        switch (e) {
          case 'n': out->push_back('\n'); break;
          case 't': out->push_back('\t'); break;
          case 'r': out->push_back('\r'); break;
          case 'b': out->push_back('\b'); break;
          case 'f': out->push_back('\f'); break;
          case '/': out->push_back('/'); break;
          case '"': out->push_back('"'); break;
          case '\\': out->push_back('\\'); break;
          case 'u': {
            if (p + 4 > s.size()) { if (err) *err = "\\u 转义不完整"; return false; }
            unsigned cp = static_cast<unsigned>(
                std::stoul(s.substr(p, 4), nullptr, 16));
            p += 4;
            // 仅处理 BMP 基本平面（够用）
            if (cp < 0x80) {
              out->push_back(static_cast<char>(cp));
            } else if (cp < 0x800) {
              out->push_back(static_cast<char>(0xC0 | (cp >> 6)));
              out->push_back(static_cast<char>(0x80 | (cp & 0x3F)));
            } else {
              out->push_back(static_cast<char>(0xE0 | (cp >> 12)));
              out->push_back(static_cast<char>(0x80 | ((cp >> 6) & 0x3F)));
              out->push_back(static_cast<char>(0x80 | (cp & 0x3F)));
            }
            break;
          }
          default: out->push_back(e); break;
        }
      } else {
        out->push_back(c);
      }
    }
    if (err) *err = "字符串未闭合";
    return false;
  }

  static bool ParseArray(const std::string& s, size_t& p, Value* out, std::string* err) {
    ++p;  // '['
    Array arr;
    SkipWs(s, p);
    if (p < s.size() && s[p] == ']') { ++p; *out = Value(std::move(arr)); return true; }
    while (p < s.size()) {
      Value v;
      if (!ParseValue(s, p, &v, err)) return false;
      arr.push_back(std::move(v));
      SkipWs(s, p);
      if (p < s.size() && s[p] == ',') { ++p; continue; }
      if (p < s.size() && s[p] == ']') { ++p; *out = Value(std::move(arr)); return true; }
      if (err) *err = "数组格式错误";
      return false;
    }
    if (err) *err = "数组未闭合";
    return false;
  }

  static bool ParseObject(const std::string& s, size_t& p, Value* out, std::string* err) {
    ++p;  // '{'
    Object obj;
    SkipWs(s, p);
    if (p < s.size() && s[p] == '}') { ++p; *out = Value(std::move(obj)); return true; }
    while (p < s.size()) {
      SkipWs(s, p);
      std::string key;
      if (!ParseString(s, p, &key, err)) return false;
      SkipWs(s, p);
      if (p >= s.size() || s[p] != ':') { if (err) *err = "对象缺少 ':'"; return false; }
      ++p;
      Value v;
      if (!ParseValue(s, p, &v, err)) return false;
      obj[key] = std::move(v);
      SkipWs(s, p);
      if (p < s.size() && s[p] == ',') { ++p; continue; }
      if (p < s.size() && s[p] == '}') { ++p; *out = Value(std::move(obj)); return true; }
      if (err) *err = "对象格式错误";
      return false;
    }
    if (err) *err = "对象未闭合";
    return false;
  }

  Type type_;
  bool bool_ = false;
  double num_ = 0.0;
  std::string str_;
  Array arr_;
  Object obj_;
};

// ---------------------------------------------------------------------------
//  Writer —— 流式构造紧凑 JSON
// ---------------------------------------------------------------------------
class Writer {
 public:
  Writer& BeginObject() { Sep(); out_ += '{'; first_.push_back(true); return *this; }
  Writer& EndObject() { out_ += '}'; first_.pop_back(); return *this; }
  Writer& BeginArray() { Sep(); out_ += '['; first_.push_back(true); return *this; }
  Writer& EndArray() { out_ += ']'; first_.pop_back(); return *this; }

  Writer& Key(const std::string& k) {
    Sep();
    out_ += '"';
    Escape(k);
    out_ += "\":";
    pending_key_ = true;
    return *this;
  }

  Writer& Str(const std::string& v) { Sep(); out_ += '"'; Escape(v); out_ += '"'; return *this; }
  Writer& Num(double v) {
    Sep();
    if (std::isnan(v) || std::isinf(v)) {
      out_ += "0";
    } else {
      char buf[64];
      std::snprintf(buf, sizeof(buf), "%.6f", v);
      out_ += buf;
    }
    return *this;
  }
  Writer& Int(long long v) { Sep(); out_ += std::to_string(v); return *this; }
  Writer& Bool(bool v) { Sep(); out_ += (v ? "true" : "false"); return *this; }
  Writer& Null() { Sep(); out_ += "null"; return *this; }

  // 便捷方法
  template <typename T>
  Writer& KV(const std::string& k, const T& v) {
    Key(k);
    return *this << v;
  }
  Writer& operator<<(const std::string& v) { return Str(v); }
  Writer& operator<<(const char* v) { return Str(v ? v : ""); }
  Writer& operator<<(double v) { return Num(v); }
  Writer& operator<<(int v) { return Int(v); }
  Writer& operator<<(long long v) { return Int(v); }
  Writer& operator<<(bool v) { return Bool(v); }

  const std::string& str() const { return out_; }

 private:
  void Sep() {
    if (pending_key_) { pending_key_ = false; return; }
    if (!first_.empty()) {
      if (!first_.back()) out_ += ',';
      first_.back() = false;
    }
  }
  void Escape(const std::string& s) {
    for (char c : s) {
      switch (c) {
        case '"': out_ += "\\\""; break;
        case '\\': out_ += "\\\\"; break;
        case '\n': out_ += "\\n"; break;
        case '\r': out_ += "\\r"; break;
        case '\t': out_ += "\\t"; break;
        default:
          if (static_cast<unsigned char>(c) < 0x20) {
            char buf[8];
            std::snprintf(buf, sizeof(buf), "\\u%04x", c);
            out_ += buf;
          } else {
            out_ += c;
          }
      }
    }
  }

  std::string out_;
  std::vector<bool> first_;
  bool pending_key_ = false;
};

}  // namespace json
}  // namespace dn
