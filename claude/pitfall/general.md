# 通用踩坑记录

## 2026-05-14 - OSS V1 签名 + STS：x-oss-security-token 必须同时出现在请求头和 StringToSign 中

**现象**: OSS 返回 403 SignatureDoesNotMatch 或 403 AccessDenied，使用 STS 临时凭证签名时发生
**根因**: OSS V1 签名规范要求，使用 STS 临时凭证时 x-oss-security-token 必须：① 作为请求头发送；② 同时出现在 StringToSign 的 CanonicalizedOSSHeaders 段（按字母序）。缺少任意一处，OSS 签名验证失败
**解决**: StringToSign 中加入 `x-oss-security-token:{token}\n`（紧接在 Date 行之后，/ 资源路径之前），同时 `req.Header.Set("x-oss-security-token", token)`
**标签**: oss, sts, v1签名, security-token, 403, 阿里云
