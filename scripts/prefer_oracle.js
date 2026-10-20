// Reads a JSON array of Prefer field values on stdin and prints, for each, the object the
// parse-prefer-header package (an independent RFC 7240 parser for Node.js) returns.
// Usage: node scripts/prefer_oracle.js <folder holding node_modules/parse-prefer-header>
const path = require("path");
const parsePreferHeader = require(path.join(process.argv[2], "node_modules", "parse-prefer-header"));

let input = "";
process.stdin.setEncoding("utf8");
process.stdin.on("data", (chunk) => {
  input += chunk;
});
process.stdin.on("end", () => {
  const out = JSON.parse(input).map((value) => parsePreferHeader(value));
  process.stdout.write(JSON.stringify(out));
});
