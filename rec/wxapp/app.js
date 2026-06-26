// app.js
const settings = require('./config/settings.js')

App({
  onLaunch() {
    console.log('App Launch')

    // 初始化全局数据，包括settings
    this.initGlobalData()

    // 检查登录状态
    this.checkLoginStatus()

    // 获取系统信息
    this.getSystemInfo()

    // 设置全局错误处理
    this.setupErrorHandler()
  },

  onShow() {
    console.log('App Show')
  },

  onHide() {
    console.log('App Hide')
  },

  // 初始化全局数据
  initGlobalData() {
    // 设置settings到全局数据
    this.globalData.settings = settings

    // 初始化其他全局数据
    this.globalData.userInfo = null
    this.globalData.isLoggedIn = false
    this.globalData.isGuest = false
    this.globalData.token = null
    this.globalData.systemInfo = null
    this.globalData.isIPhoneX = false
    this.globalData.navBarHeight = 0
    this.globalData.tabPages = []

    console.log('Settings loaded:', settings.baseUrl)
  },

  // 设置错误处理
  setupErrorHandler() {
    // 监听小程序错误
    wx.onError((error) => {
      console.error('小程序错误:', error)
      this.logError('app_error', error)
    })

    // 监听页面不存在错误
    wx.onPageNotFound((res) => {
      console.error('页面不存在:', res)
      wx.redirectTo({
        url: '/pages/index/index'
      })
    })
  },

  // 记录错误日志
  logError(type, error) {
    const errorLog = {
      type: type,
      timestamp: new Date().toISOString(),
      error: error,
      userInfo: this.globalData.userInfo,
      systemInfo: this.globalData.systemInfo
    }

    console.error('[App Error]', errorLog)
  },

  // 检查登录状态
  checkLoginStatus() {
    const token = wx.getStorageSync('token')
    const userInfo = wx.getStorageSync('userInfo')
    const isLogin = wx.getStorageSync('isLogin')
    const isGuest = wx.getStorageSync('isGuest')

    // 检查专门的员工登录状态
    const employeeToken = wx.getStorageSync('employeeToken')
    const employeeInfo = wx.getStorageSync('employeeInfo')

    // 设置用户登录状态
    this.globalData.isLoggedIn = isLogin || false
    this.globalData.userInfo = userInfo || null
    this.globalData.token = token || null
    this.globalData.isGuest = isGuest || false

    // 设置员工登录状态
    this.globalData.isEmployeeLoggedIn = !!employeeToken
    this.globalData.employeeInfo = employeeInfo || null
    this.globalData.employeeToken = employeeToken || null

    // 检查普通用户是否为员工，如果是则自动设置员工状态
    if (userInfo && !this.globalData.isEmployeeLoggedIn) {
      const isEmployee = userInfo.is_staff_member ||
        userInfo.user_type === 'employee' ||
        userInfo.user_type === 'admin'
      const hasStaffId = userInfo.staff_id && userInfo.staff_id.trim() !== ''

      if (isEmployee && hasStaffId) {
        console.log('[App] 普通用户是员工，自动设置员工状态')
        this.globalData.isEmployeeLoggedIn = true
        this.globalData.employeeInfo = userInfo
        this.globalData.employeeToken = token

        // 保存到专门的员工存储
        if (!employeeToken) {
          wx.setStorageSync('employeeToken', token)
        }
        if (!employeeInfo) {
          wx.setStorageSync('employeeInfo', userInfo)
        }
      }
    }

    console.log('App登录状态:', this.globalData)

    // 如果已登录，检查token有效性
    if (this.globalData.isLoggedIn && token) {
      this.checkTokenValidity()
    }

    // 如果员工已登录，检查token有效性
    if (this.globalData.isEmployeeLoggedIn && this.globalData.employeeToken) {
      this.checkEmployeeTokenValidity()
    }
  },

  // 检查token有效性
  checkTokenValidity() {
    const loginTime = wx.getStorageSync('loginTime')
    if (!loginTime) return

    const now = new Date().getTime()
    const tokenAge = now - loginTime
    const sevenDays = 7 * 24 * 60 * 60 * 1000

    // 如果token使用超过6天，提示用户重新登录
    if (tokenAge > 6 * 24 * 60 * 60 * 1000) {
      console.log('Token即将过期，建议更新')
    }
  },

  // 检查员工token有效性
  checkEmployeeTokenValidity() {
    const employeeLoginTime = wx.getStorageSync('employeeLoginTime')
    if (!employeeLoginTime) return

    const now = new Date().getTime()
    const tokenAge = now - employeeLoginTime
    const oneDay = 24 * 60 * 60 * 1000

    // 如果员工token超过23小时，提示刷新
    if (tokenAge > 23 * 60 * 60 * 1000) {
      console.log('员工Token即将过期，建议刷新')
    }
  },

  // 获取系统信息
  getSystemInfo() {
    wx.getSystemInfo({
      success: (res) => {
        this.globalData.systemInfo = res
        this.globalData.isIPhoneX = /iPhone X/.test(res.model)

        // 设置导航栏高度
        this.globalData.navBarHeight = res.statusBarHeight + 44

        // 设置tab页列表
        this.globalData.tabPages = [
          '/pages/index/index',
          '/pages/mall/index/index',
          '/pages/news/index/index',
          '/pages/user/index/index'
        ]
      }
    })
  },

  // 全局登录方法（普通用户）
  globalLogin() {
    return new Promise((resolve, reject) => {
      if (this.globalData.isLoggedIn) {
        resolve(this.globalData.userInfo)
        return
      }

      const currentPage = this.getCurrentPage()

      wx.navigateTo({
        url: `/pages/user/login/login?redirect=${encodeURIComponent(currentPage)}`,
        success: () => {
          // 监听登录成功事件
          const onLoginSuccess = (userInfo) => {
            resolve(userInfo)
            // 移除监听
            this.offLoginSuccess(onLoginSuccess)
          }

          this.onLoginSuccess(onLoginSuccess)
        },
        fail: reject
      })
    })
  },

  // 员工登录方法
  employeeLogin() {
    return new Promise((resolve, reject) => {
      if (this.globalData.isEmployeeLoggedIn) {
        resolve(this.globalData.employeeInfo)
        return
      }

      const currentPage = this.getCurrentPage()

      wx.navigateTo({
        url: `/pages/user/employeepassage/employeepassage?redirect=${encodeURIComponent(currentPage)}`,
        success: () => {
          // 监听员工登录成功事件
          const onEmployeeLoginSuccess = (employeeInfo) => {
            resolve(employeeInfo)
            // 移除监听
            this.offEmployeeLoginSuccess(onEmployeeLoginSuccess)
          }

          this.onEmployeeLoginSuccess(onEmployeeLoginSuccess)
        },
        fail: reject
      })
    })
  },

  // 获取当前页面路径
  getCurrentPage() {
    const pages = getCurrentPages()
    const currentPage = pages[pages.length - 1]
    return `/${currentPage.route}`
  },

  // 自动登录（使用本地存储的token） 
  autoLogin() {
    return new Promise((resolve, reject) => {
      const token = wx.getStorageSync('token')
      const userInfo = wx.getStorageSync('userInfo')

      if (!token || !userInfo) {
        reject(new Error('没有找到登录信息'))
        return
      }

      // 更新全局状态
      this.globalData.isLoggedIn = true
      this.globalData.userInfo = userInfo
      this.globalData.token = token
      this.globalData.isGuest = false

      resolve(userInfo)
    })
  },

  // 员工自动登录
  autoEmployeeLogin() {
    return new Promise((resolve, reject) => {
      const employeeToken = wx.getStorageSync('employeeToken')
      const employeeInfo = wx.getStorageSync('employeeInfo')

      if (!employeeToken || !employeeInfo) {
        reject(new Error('没有找到员工登录信息'))
        return
      }

      // 更新全局状态
      this.globalData.isEmployeeLoggedIn = true
      this.globalData.employeeInfo = employeeInfo
      this.globalData.employeeToken = employeeToken

      resolve(employeeInfo)
    })
  },

  // 登录成功事件监听（普通用户）
  onLoginSuccess(callback) {
    if (!this._loginCallbacks) {
      this._loginCallbacks = []
    }
    this._loginCallbacks.push(callback)
  },

  offLoginSuccess(callback) {
    if (this._loginCallbacks) {
      const index = this._loginCallbacks.indexOf(callback)
      if (index > -1) {
        this._loginCallbacks.splice(index, 1)
      }
    }
  },

  emitLoginSuccess(userInfo) {
    if (this._loginCallbacks) {
      this._loginCallbacks.forEach(callback => {
        try {
          callback(userInfo)
        } catch (e) {
          console.error('Login callback error:', e)
        }
      })
      this._loginCallbacks = []
    }
  },

  // 员工登录成功事件监听
  onEmployeeLoginSuccess(callback) {
    if (!this._employeeLoginCallbacks) {
      this._employeeLoginCallbacks = []
    }
    this._employeeLoginCallbacks.push(callback)
  },

  offEmployeeLoginSuccess(callback) {
    if (this._employeeLoginCallbacks) {
      const index = this._employeeLoginCallbacks.indexOf(callback)
      if (index > -1) {
        this._employeeLoginCallbacks.splice(index, 1)
      }
    }
  },

  emitEmployeeLoginSuccess(employeeInfo) {
    if (this._employeeLoginCallbacks) {
      this._employeeLoginCallbacks.forEach(callback => {
        try {
          callback(employeeInfo)
        } catch (e) {
          console.error('Employee login callback error:', e)
        }
      })
      this._employeeLoginCallbacks = []
    }
  },

  // 更新用户信息
  updateUserInfo(userInfo) {
    this.globalData.userInfo = userInfo
    wx.setStorageSync('userInfo', userInfo)

    // 触发用户信息更新事件
    if (this._userInfoUpdateCallbacks) {
      this._userInfoUpdateCallbacks.forEach(callback => {
        try {
          callback(userInfo)
        } catch (e) {
          console.error('UserInfo update callback error:', e)
        }
      })
    }
  },

  // 更新员工信息
  updateEmployeeInfo(employeeInfo) {
    this.globalData.employeeInfo = employeeInfo
    wx.setStorageSync('employeeInfo', employeeInfo)

    // 触发员工信息更新事件
    if (this._employeeInfoUpdateCallbacks) {
      this._employeeInfoUpdateCallbacks.forEach(callback => {
        try {
          callback(employeeInfo)
        } catch (e) {
          console.error('EmployeeInfo update callback error:', e)
        }
      })
    }
  },

  // 用户信息更新监听
  onUserInfoUpdate(callback) {
    if (!this._userInfoUpdateCallbacks) {
      this._userInfoUpdateCallbacks = []
    }
    this._userInfoUpdateCallbacks.push(callback)
  },

  offUserInfoUpdate(callback) {
    if (this._userInfoUpdateCallbacks) {
      const index = this._userInfoUpdateCallbacks.indexOf(callback)
      if (index > -1) {
        this._userInfoUpdateCallbacks.splice(index, 1)
      }
    }
  },

  // 员工信息更新监听
  onEmployeeInfoUpdate(callback) {
    if (!this._employeeInfoUpdateCallbacks) {
      this._employeeInfoUpdateCallbacks = []
    }
    this._employeeInfoUpdateCallbacks.push(callback)
  },

  offEmployeeInfoUpdate(callback) {
    if (this._employeeInfoUpdateCallbacks) {
      const index = this._employeeInfoUpdateCallbacks.indexOf(callback)
      if (index > -1) {
        this._employeeInfoUpdateCallbacks.splice(index, 1)
      }
    }
  },

  // 检查权限
  checkPermission(permission) {
    const userInfo = this.globalData.userInfo
    if (!userInfo) return false

    // 根据用户角色检查权限
    switch (permission) {
      case 'staff':
        return userInfo.is_staff_member || false
      case 'verified':
        return userInfo.is_verified || false
      default:
        return true
    }
  },

  // 检查员工权限
  checkEmployeePermission(requiredType = 'employee') {
    const employeeInfo = this.globalData.employeeInfo
    if (!employeeInfo) return false

    // 检查员工类型
    const userType = employeeInfo.user_type || employeeInfo.ocr_user_type
    if (!userType) return false

    if (requiredType === 'admin') {
      return userType === 'admin'
    } else if (requiredType === 'employee') {
      return userType === 'employee' || userType === 'admin'
    }

    return false
  },

  // 检查页面是否是tab页
  isTabPage(pagePath) {
    return this.globalData.tabPages && this.globalData.tabPages.includes(pagePath)
  },

  // 获取API完整URL
  getApiUrl(endpoint) {
    if (!this.globalData.settings) {
      console.error('Settings not loaded')
      return ''
    }

    const baseUrl = this.globalData.settings.baseUrl
    if (!endpoint) return baseUrl

    // 如果endpoint已经是完整URL，直接返回
    if (endpoint.startsWith('http')) {
      return endpoint
    }

    // 如果endpoint以/开头，直接拼接
    if (endpoint.startsWith('/')) {
      return baseUrl + endpoint
    }

    // 否则添加/
    return baseUrl + '/' + endpoint
  },

  // 通用请求方法
  request(options) {
    const that = this

    return new Promise((resolve, reject) => {
      // 获取token（优先使用员工token，如果没有则使用普通用户token）
      const token = that.globalData.employeeToken || that.globalData.token

      // 构建完整URL
      let url = options.url
      if (!url.startsWith('http')) {
        url = that.getApiUrl(url)
      }

      // 设置默认header
      const header = {
        'Content-Type': 'application/json',
        ...options.header
      }

      // 添加token
      if (token) {
        header['Authorization'] = `Bearer ${token}`
      }

      wx.request({
        url: url,
        method: options.method || 'GET',
        data: options.data || {},
        header: header,
        success: function (res) {
          if (res.statusCode === 200) {
            resolve(res.data)
          } else {
            reject({
              status: res.statusCode,
              message: res.data && res.data.message ? res.data.message : '请求失败',
              data: res.data
            })
          }
        },
        fail: function (err) {
          reject({
            status: 0,
            message: '网络请求失败',
            error: err
          })
        }
      })
    })
  },

  globalData: {
    // 配置信息
    settings: null,

    // 普通用户信息
    userInfo: null,
    isLoggedIn: false,
    isGuest: false,
    token: null,

    // 员工信息
    employeeInfo: null,
    isEmployeeLoggedIn: false,
    employeeToken: null,

    // 系统信息
    systemInfo: null,
    isIPhoneX: false,
    navBarHeight: 0,
    tabPages: []
  }
})