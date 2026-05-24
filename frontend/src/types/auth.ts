/** 用户角色由服务端定义，客户端仅用于 UI 展示控制 */
export type UserRole = 'admin' | 'user'

export interface AuthUser {
  email: string
  role: UserRole
}

/** 登录 / 注册成功时服务端返回 */
export interface LoginResult {
  token: string
  user: AuthUser
}
