/** 与后端约定的认证错误码 */
export const AUTH_CODE_OK = 0
/** 密码错误（账号已存在） */
export const AUTH_CODE_WRONG_PASSWORD = 40003
/** 邮箱未注册，应进入验证码注册流程 */
export const AUTH_CODE_NOT_REGISTERED = 40403
/** 验证码发送过于频繁 */
export const AUTH_CODE_SEND_TOO_FREQUENT = 42901
/** 未登录或 token 失效 */
export const AUTH_CODE_UNAUTHORIZED = 40101
