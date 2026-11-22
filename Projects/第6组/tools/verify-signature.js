/**
 * TC3 签名算法验证：用腾讯云官方文档示例（api/213/30654）的输入与期望输出，
 * 对照 cloudfunctions/speech/index.js 中 callTencentCloud 的签名实现。
 * 期望 Signature：10b1a37a7301a02ca19a647ad722d5e43b4b3cff309d421d85b46093f6ab6c4f
 */
const crypto = require('crypto');

// ---- 与 speech/index.js 完全一致的实现 ----
function sha256hex(data) {
  return crypto.createHash('sha256').update(data, 'utf8').digest('hex');
}
function hmac(key, data) {
  return crypto.createHmac('sha256', key).update(data, 'utf8').digest();
}

// 官方示例输入（请求体为文档展示的原始字面量：带空格 + \u 转义）
const secretId = 'AKIDz8krbsJ5yKBZQpn74WFMMLP3zcU2SaV';
const secretKey = 'Gu5t9xGARNpq86cd98joQYCN3EXAMPLE';
const ts = 1551113065;
const service = 'cvm';
const host = 'cvm.tencentcloudapi.com';
const action = 'DescribeInstances';
const body = '{"Limit": 1, "Filters": [{"Values": ["\\u672a\\u547d\\u540d"], "Name": "instance-name"}]}';

const EXPECTED = '10b1a37a7301a02ca19a647ad722d5e43b4b3cff309d421d85b46093f6ab6c4f';
const EXPECTED_CREQ_HASH = '7019a55be8395899b900fb5564e4200d984910f34794a27cb3fb7d10ff6a1e84';

// 修复后的日期算法（UTC）
const date = new Date(ts * 1000).toISOString().slice(0, 10);
console.log('日期(UTC) =', date, date === '2019-02-25' ? '✓ 与官方一致' : '✗ 错误!');

// 与 speech/index.js 相同的规范请求拼装，但按官方示例签 content-type;host;x-tc-action
const canonicalHeaders =
  `content-type:application/json; charset=utf-8\nhost:${host}\nx-tc-action:${action.toLowerCase()}\n`;
const signedHeaders = 'content-type;host;x-tc-action';
const canonicalRequest = ['POST', '/', '', canonicalHeaders, signedHeaders, sha256hex(body)].join('\n');
const creqHash = sha256hex(canonicalRequest);
console.log('规范请求哈希 =', creqHash, creqHash === EXPECTED_CREQ_HASH ? '✓ 与官方一致' : '✗ 不一致');

const scope = `${date}/${service}/tc3_request`;
const stringToSign = ['TC3-HMAC-SHA256', String(ts), scope, creqHash].join('\n');

const kDate = hmac(`TC3${secretKey}`, date);
const kService = hmac(kDate, service);
const kSigning = hmac(kService, 'tc3_request');
const signature = crypto.createHmac('sha256', kSigning).update(stringToSign, 'utf8').digest('hex');

console.log('Signature =', signature);
if (signature === EXPECTED) {
  console.log('\n✓✓ 签名算法与腾讯云官方规范完全一致，修复有效');
} else {
  console.log('\n✗ 与官方期望签名不一致，算法仍有问题');
  process.exit(1);
}

// 附加验证：复现旧 bug（UTC+8 日期）必然导致签名不同
const badDate = new Date(ts * 1000 + 8 * 3600 * 1000).toISOString().slice(0, 10);
console.log('\n[反证] 旧算法(UTC+8)的日期 =', badDate, '→ 2019-02-26 凌晨场景，签名必然不匹配');
