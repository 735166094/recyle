const app = getApp()
const settings = require('../../../config/settings.js')

Page({
  data: {
    agreementChecked: false,
    showAgreementModal: false,
    agreementTitle: '',
    agreementContent: '',
    isLoggingIn: false,
    loginStep: 1,
    animationData: {},
    showWelcome: true,
    showUnifiedAlert: false,
    unifiedAlertTitle: '',
    unifiedAlertContent: '',
    unifiedAlertActions: [],
    redirectUrl: null,
    isGettingUserProfile: false,
    currentLoginCode: null,
    networkAvailable: true,
    loginRetryCount: 0,
    maxRetryCount: 3,
    isFromRedirect: false,
    showLoginMethods: false,
    showAgreementAlert: false,
    phoneMaskContext: null,
    // 记录来源页面
    fromPage: null,
    // 保存登录前的页面栈
    pageStack: []
  },

  onLoad(options) {
    console.log('[Login] 页面加载，参数:', options)

    // 获取当前页面栈
    const pages = getCurrentPages()
    this.setData({
      pageStack: pages.map(page => page.route)
    })

    // 处理重定向URL 
    if (options.redirect) {
      let redirectUrl = decodeURIComponent(options.redirect)

      // 再次检查是否有双重编码 
      // 如果URL中还有%2F等编码字符，说明可能被编码了两次
      if (redirectUrl.includes('%2F') || redirectUrl.includes('%3F') || redirectUrl.includes('%3D')) {
        console.log('[Login] 检测到双重编码的URL，再次解码:', redirectUrl)
        try {
          redirectUrl = decodeURIComponent(redirectUrl)
        } catch (e) {
          console.error('[Login] URL解码失败:', e)
        }
      }

      console.log('[Login] 处理后的重定向URL:', redirectUrl)

      this.setData({
        redirectUrl: redirectUrl,
        isFromRedirect: true
      })
    }

    // 记录来源页面
    if (options.from) {
      this.setData({
        fromPage: options.from
      })
    }

    this.animateIn()
    this.checkNetworkStatus()

    // 延迟显示登录方式，避免与欢迎动画冲突
    setTimeout(() => {
      this.setData({
        showWelcome: false,
        showLoginMethods: true
      })
    }, 2000)
  },

  onShow() {
    console.log('[Login] 页面显示')
    this.checkLoginStatus()
    this.checkNetworkStatus()

    // 页面显示时获取手机号掩码上下文
    this.getPhoneMaskContext()
  },

  onHide() {
    console.log('[Login] 页面隐藏')
  },

  onUnload() {
    console.log('[Login] 页面卸载')
  },

  /**
   * 获取手机号掩码上下文（前置流程）
   */
  getPhoneMaskContext() {
    if (wx.getPhoneMask) {
      wx.getPhoneMask({
        success: (res) => {
          console.log('[Login] 获取手机号掩码上下文成功:', res)
          this.setData({
            phoneMaskContext: res
          })
        },
        fail: (err) => {
          console.error('[Login] 获取手机号掩码上下文失败:', err)
        }
      })
    }
  },

  /**
   * 检查网络状态
   */
  checkNetworkStatus() {
    wx.getNetworkType({
      success: (res) => {
        const networkType = res.networkType
        const available = networkType !== 'none'
        this.setData({
          networkAvailable: available
        })

        if (!available) {
          console.warn('[Login] 网络不可用')
          this.showSimpleToast('网络连接不可用，请检查网络设置', 'none')
        }
      },
      fail: () => {
        this.setData({
          networkAvailable: false
        })
      }
    })
  },

  /**
   * 入场动画
   */
  animateIn() {
    const animation = wx.createAnimation({
      duration: 600,
      timingFunction: 'ease-out'
    })

    animation.opacity(1).translateY(0).step()

    this.setData({
      animationData: animation.export()
    })
  },

  /**
   * 检查登录状态
   */
  checkLoginStatus() {
    const token = wx.getStorageSync('token')
    const userInfo = wx.getStorageSync('userInfo')
    const isLogin = wx.getStorageSync('isLogin')

    if (token && userInfo && isLogin) {
      console.log('[Login] 检测到已登录，自动跳转')
      this.redirectAfterLogin()
    }
  },

  /**
   * 微信一键登录主入口
   */
  handleWechatLogin() {
    if (!this.data.networkAvailable) {
      this.showSimpleToast('网络连接不可用，请检查网络设置', 'none')
      return
    }

    if (this.data.isLoggingIn || this.data.isGettingUserProfile) {
      console.log('[Login] 登录进行中，忽略重复点击')
      return
    }

    if (!this.data.agreementChecked) {
      // 显示新的温馨提示弹窗
      this.setData({
        showAgreementAlert: true
      })
      return
    }

    this.executeWechatLogin()
  },

  /**
   * 本机号码一键登录
   */
  handlePhoneOneClickLogin() {
    if (!this.data.networkAvailable) {
      this.showSimpleToast('网络连接不可用，请检查网络设置', 'none')
      return
    }

    if (this.data.isLoggingIn) {
      console.log('[Login] 登录进行中，忽略重复点击')
      return
    }

    if (!this.data.agreementChecked) {
      this.setData({
        showAgreementAlert: true
      })
      return
    }

    // 检查是否已获取手机号掩码上下文
    if (!this.data.phoneMaskContext) {
      this.showUnifiedAlert({
        title: '提示',
        content: '请先获取手机号权限',
        actions: [{
          text: '重新获取',
          type: 'primary',
          handler: () => {
            this.hideUnifiedAlert()
            this.getPhoneMaskContext()
            // 重新尝试一键登录
            setTimeout(() => {
              this.handlePhoneOneClickLogin()
            }, 500)
          }
        }, {
          text: '取消',
          type: 'cancel',
          handler: () => this.hideUnifiedAlert()
        }]
      })
      return
    }

    console.log('[Login] 开始本机号码一键登录')
    this.executePhoneOneClickLogin()
  },

  /**
   * 执行本机号码一键登录
   */
  executePhoneOneClickLogin() {
    this.setData({
      isLoggingIn: true,
      loginStep: 1
    })

    wx.showLoading({
      title: '正在登录...',
      mask: true
    })

    // 这里会触发 button 组件的 phoneOneClickLogin 事件
    // 实际登录逻辑在 onHandlePhoneOneClickLogin 方法中
  },

  /**
   * 本机号码一键登录回调
   */
  onHandlePhoneOneClickLogin(e) {
    const detail = e.detail
    console.log('[Login] 本机号码一键登录回调:', detail)

    if (detail.errCode === 0 && detail.code) {
      console.log('[Login] 获取到登录凭证code:', detail.code)
      // 调用后端接口进行登录
      this.loginWithPhoneOneClickCode(detail.code)
    } else {
      wx.hideLoading()
      this.resetLoginState()

      let errorMsg = '一键登录失败'
      switch (detail.errCode) {
        case -1:
          errorMsg = '系统错误，请重试'
          break
        case 10001021:
          errorMsg = '该手机号已登录过，请使用其他方式登录'
          break
        default:
          errorMsg = `登录失败，错误码: ${detail.errCode}`
      }

      this.showSimpleToast(errorMsg, 'none')
    }
  },

  /**
   * 使用本机号码一键登录凭证登录
   */
  loginWithPhoneOneClickCode(code) {
    console.log('[Login] 使用一键登录凭证登录:', code)

    this.setData({
      loginStep: 2
    })

    // 同时获取用户信息，确保在同一个用户点击事件中
    this.getUserInfoForPhoneLogin((userInfo) => {
      this.callPhoneOneClickLogin(code, userInfo)
    })
  },

  /**
   * 为手机号登录获取用户信息
   */
  getUserInfoForPhoneLogin(callback) {
    wx.getUserProfile({
      desc: '用于完善会员资料和个性化服务',
      success: (res) => {
        console.log('[Login] 获取用户信息成功')
        const processedUserInfo = this.processUserInfo(res.userInfo)
        callback(processedUserInfo)
      },
      fail: (err) => {
        console.log('[Login] 用户拒绝授权:', err)
        // 用户拒绝授权，使用空用户信息
        callback(null)
      }
    })
  },

  /**
   * 调用后端本机号码一键登录接口
   */
  callPhoneOneClickLogin(code, userInfo) {
    console.log('[Login] 调用后端本机号码一键登录接口')

    this.setData({
      loginStep: 3
    })

    wx.showLoading({
      title: '登录中...',
      mask: true
    })

    const requestData = {
      code: code,
      user_info: userInfo
    }

    console.log('[Login] 发送登录请求:', {
      url: settings.userWechatPhoneLogin,
      data: requestData
    })

    wx.request({
      url: settings.userWechatPhoneLogin,
      method: 'POST',
      header: {
        'Content-Type': 'application/json'
      },
      data: requestData,
      success: (res) => {
        wx.hideLoading()
        console.log('[Login] 登录响应:', res.data)

        if (res.statusCode === 200 && res.data.code === 200) {
          console.log('[Login] 本机号码一键登录成功')
          this.resetLoginState()
          this.handleLoginSuccess(res.data.data)
        } else {
          console.error('[Login] 登录失败:', res.data)
          this.resetLoginState()

          let errorMsg = res.data.message || `登录失败 (${res.statusCode})`
          if (res.data.errors) {
            errorMsg = `${errorMsg}: ${JSON.stringify(res.data.errors)}`
          }

          this.showUnifiedAlert({
            title: '登录失败',
            content: errorMsg,
            actions: [{
              text: '重试',
              type: 'primary',
              handler: () => {
                this.hideUnifiedAlert()
                this.executePhoneOneClickLogin()
              }
            }, {
              text: '其他方式登录',
              type: 'cancel',
              handler: () => {
                this.hideUnifiedAlert()
                this.resetLoginState()
              }
            }]
          })
        }
      },
      fail: (err) => {
        console.error('[Login] 登录请求失败:', err)
        wx.hideLoading()
        this.resetLoginState()
        this.showSimpleToast('网络错误，请检查网络后重试', 'none')
      }
    })
  },

  /**
   * 获取手机号 
   */
  getPhoneNumber(event) {
    console.log('[Login] getPhoneNumber事件:', event)

    if (!this.data.agreementChecked) {
      this.setData({
        showAgreementAlert: true
      })
      return
    }

    if (!event.detail || !event.detail.code) {
      console.warn('[Login] 未获取到手机号code')

      // 用户拒绝授权
      if (event.detail && event.detail.errMsg && event.detail.errMsg.includes('deny')) {
        this.showUnifiedAlert({
          title: '授权提示',
          content: '需要手机号授权才能快速登录',
          actions: [{
            text: '手动输入',
            type: 'primary',
            handler: () => {
              this.hideUnifiedAlert()
              this.handlePhoneLogin()
            }
          }, {
            text: '知道了',
            type: 'cancel',
            handler: () => this.hideUnifiedAlert()
          }]
        })
      }
      return
    }

    const code = event.detail.code
    console.log('[Login] 获取到手机号code:', code)

    // 获取用户信息
    this.getUserInfoForPhoneLogin((userInfo) => {
      // 调用后端接口
      this.callWechatPhoneLogin(code, userInfo)
    })
  },

  /**
   * 调用微信手机号登录接口 
   * 手机号已存在时直接登录，不再创建新账号
   */
  callWechatPhoneLogin(code, userInfo) {
    console.log('[Login] 调用微信手机号登录接口')

    this.setData({
      isLoggingIn: true,
      loginStep: 1
    })

    wx.showLoading({
      title: '登录中...',
      mask: true
    })

    const requestData = {
      code: code,
      user_info: userInfo
    }

    wx.request({
      url: settings.userWechatPhoneLogin,
      method: 'POST',
      header: {
        'Content-Type': 'application/json'
      },
      data: requestData,
      success: (res) => {
        wx.hideLoading()
        console.log('[Login] 登录响应:', res.data)

        if (res.statusCode === 200 && res.data.code === 200) {
          console.log('[Login] 微信手机号登录成功')
          this.resetLoginState()
          this.handleLoginSuccess(res.data.data)
        } else if (res.statusCode === 400 && res.data.message && res.data.message.includes('手机号已注册')) {
          // 手机号已注册，提示用户使用其他方式登录
          console.warn('[Login] 手机号已注册')
          this.resetLoginState()
          this.showUnifiedAlert({
            title: '手机号已注册',
            content: '该手机号已注册，请使用微信登录或密码登录',
            actions: [{
              text: '微信登录',
              type: 'primary',
              handler: () => {
                this.hideUnifiedAlert()
                this.executeWechatLogin()
              }
            }, {
              text: '密码登录',
              type: 'cancel',
              handler: () => {
                this.hideUnifiedAlert()
                wx.navigateTo({
                  url: '/pages/user/auth/phone-login'
                })
              }
            }]
          })
        } else {
          console.error('[Login] 登录失败:', res.data)
          this.resetLoginState()

          let errorMsg = res.data.message || `登录失败 (${res.statusCode})`
          this.showSimpleToast(errorMsg, 'none')
        }
      },
      fail: (err) => {
        console.error('[Login] 登录请求失败:', err)
        wx.hideLoading()
        this.resetLoginState()
        this.showSimpleToast('网络错误，请检查网络后重试', 'none')
      }
    })
  },

  /**
   * 隐藏温馨提示弹窗
   */
  hideAgreementAlert() {
    this.setData({
      showAgreementAlert: false
    })
  },

  /**
   * 同意协议并登录
   */
  agreeAndLogin() {
    this.setData({
      agreementChecked: true,
      showAgreementAlert: false
    })
    this.executeWechatLogin()
  },

  /**
   * 从温馨提示弹窗跳转到用户协议
   */
  showUserAgreementFromAlert() {
    this.setData({
      showAgreementAlert: false
    })
    this.showUserAgreement()
  },

  /**
   * 从温馨提示弹窗跳转到隐私政策
   */
  showPrivacyPolicyFromAlert() {
    this.setData({
      showAgreementAlert: false
    })
    this.showPrivacyPolicy()
  },

  /**
   * 执行微信登录流程  
   */
  executeWechatLogin() {
    console.log('[Login] 开始执行微信登录')

    this.setData({
      isLoggingIn: true,
      loginStep: 1,
      loginRetryCount: 0
    })

    wx.showLoading({
      title: '获取登录凭证...',
      mask: true
    })

    // 同时获取微信code和用户信息，确保都在用户点击事件中
    this.getWechatCodeAndUserInfo()
  },

  /**
   * 同时获取微信code和用户信息
   */
  getWechatCodeAndUserInfo() {
    // 第一步：获取微信登录code
    wx.login({
      success: (loginRes) => {
        if (loginRes.code) {
          console.log('[Login] 获取微信code成功:', loginRes.code)

          // 保存当前的code
          this.setData({
            currentLoginCode: loginRes.code
          })

          // 第二步：立即获取用户基本信息（在同一个用户点击事件中）
          this.getUserProfile(loginRes.code)
        } else {
          console.error('[Login] 获取微信code失败')
          wx.hideLoading()
          this.resetLoginState()
          this.handleLoginError('获取登录凭证失败，请重试')
        }
      },
      fail: (err) => {
        console.error('[Login] wx.login调用失败:', err)
        wx.hideLoading()
        this.resetLoginState()
        this.handleLoginError('登录失败，请检查网络后重试')
      }
    })
  },

  /**
   * 获取用户详细信息 
   */
  getUserProfile(code) {
    console.log('[Login] 开始获取用户信息')

    if (this.data.isGettingUserProfile) {
      return
    }

    this.setData({
      loginStep: 2,
      isGettingUserProfile: true
    })

    wx.showLoading({
      title: '获取用户信息...',
      mask: true
    })

    wx.getUserProfile({
      desc: '用于完善会员资料和个性化服务',
      success: (res) => {
        console.log('[Login] 获取用户信息成功')

        wx.hideLoading()
        this.setData({
          isGettingUserProfile: false
        })

        // 处理用户信息格式，确保符合后端要求
        const processedUserInfo = this.processUserInfo(res.userInfo)

        // 第三步：调用后端微信登录接口 - 只传递用户信息，不传递加密数据
        this.callWechatLogin(code, null, null, processedUserInfo)
      },
      fail: (err) => {
        console.log('[Login] 用户拒绝授权或获取失败:', err)
        wx.hideLoading()
        this.setData({
          isGettingUserProfile: false
        })

        // 用户拒绝授权，直接使用基础登录（不带用户信息）
        this.showUnifiedAlert({
          title: '授权提示',
          content: '授权用户信息可以获得更好的个性化体验，是否重新授权？',
          actions: [{
              text: '继续登录',
              type: 'primary',
              handler: () => {
                this.hideUnifiedAlert()
                // 直接使用基础登录，不带用户信息
                this.callWechatLogin(code, null, null, null)
              }
            },
            {
              text: '重新授权',
              type: 'confirm',
              handler: () => {
                this.hideUnifiedAlert()
                // 重新获取用户信息，使用保存的code
                if (this.data.currentLoginCode) {
                  this.getUserProfile(this.data.currentLoginCode)
                } else {
                  // 如果没有保存的code，重新执行整个登录流程
                  this.executeWechatLogin()
                }
              }
            }
          ]
        })
      }
    })
  },

  /**
   * 处理用户信息格式，确保符合后端要求
   */
  processUserInfo(userInfo) {
    if (!userInfo) return null

    return {
      nickName: userInfo.nickName || '',
      avatarUrl: userInfo.avatarUrl || '',
      gender: userInfo.gender || 0,
      country: userInfo.country || '',
      province: userInfo.province || '',
      city: userInfo.city || ''
    }
  },

  /**
   * 调用后端微信登录接口  
   */
  callWechatLogin(code, encryptedData, iv, userInfo) {
    console.log('[Login] 调用后端登录接口')

    this.setData({
      loginStep: 3
    })

    wx.showLoading({
      title: '登录中...',
      mask: true
    })

    // 构建请求数据，确保格式正确
    const requestData = this.buildLoginRequestData(code, encryptedData, iv, userInfo)

    console.log('[Login] 发送登录请求:', {
      url: settings.userWechatLogin,
      data: requestData
    })

    wx.request({
      url: settings.userWechatLogin,
      method: 'POST',
      header: {
        'Content-Type': 'application/json'
      },
      data: requestData,
      success: (res) => {
        wx.hideLoading()
        console.log('[Login] 登录响应:', res.data)

        if (res.statusCode === 200 && res.data.code === 200) {
          console.log('[Login] 微信登录成功')
          this.resetLoginState()
          this.handleLoginSuccess(res.data.data)
        } else {
          console.error('[Login] 登录失败:', res.data)

          // 增加重试次数
          const newRetryCount = this.data.loginRetryCount + 1
          this.setData({
            loginRetryCount: newRetryCount
          })

          // 如果是参数错误，尝试不带用户信息重新登录
          if (res.data.code === 400 && userInfo && newRetryCount <= this.data.maxRetryCount) {
            console.log('[Login] 参数错误，尝试不带用户信息重新登录')
            this.callWechatLogin(code, null, null, null)
          } else if (newRetryCount <= this.data.maxRetryCount) {
            // 其他错误，提示用户重试
            this.showRetryAlert(res.data.message || `登录失败 (${res.statusCode})`)
          } else {
            this.resetLoginState()
            const errorMsg = res.data.message || `登录失败 (${res.statusCode})`

            // 显示详细的错误信息
            if (res.data.errors) {
              this.handleLoginError(`${errorMsg}: ${JSON.stringify(res.data.errors)}`)
            } else {
              this.handleLoginError(errorMsg)
            }
          }
        }
      },
      fail: (err) => {
        console.error('[Login] 登录请求失败:', err)
        wx.hideLoading()

        // 增加重试次数
        const newRetryCount = this.data.loginRetryCount + 1
        this.setData({
          loginRetryCount: newRetryCount
        })

        if (newRetryCount <= this.data.maxRetryCount) {
          this.showRetryAlert('网络错误，请检查网络后重试')
        } else {
          this.resetLoginState()
          this.handleLoginError('网络错误，请检查网络后重试')
        }
      }
    })
  },

  /**
   * 显示重试提示
   */
  showRetryAlert(errorMsg) {
    this.showUnifiedAlert({
      title: '登录失败',
      content: `${errorMsg}，是否重试？`,
      actions: [{
          text: '取消',
          type: 'cancel',
          handler: () => {
            this.hideUnifiedAlert()
            this.resetLoginState()
          }
        },
        {
          text: '重试',
          type: 'confirm',
          handler: () => {
            this.hideUnifiedAlert()
            if (this.data.currentLoginCode) {
              this.executeWechatLogin()
            } else {
              this.executeWechatLogin()
            }
          }
        }
      ]
    })
  },

  /**
   * 处理登录错误
   */
  handleLoginError(errorMsg) {
    console.error('[Login] 登录错误:', errorMsg)
    this.showSimpleToast(errorMsg, 'none')

    // 记录错误日志
    this.logError('login_error', {
      error: errorMsg,
      step: this.data.loginStep,
      retryCount: this.data.loginRetryCount
    })
  },

  /**
   * 记录错误日志
   */
  logError(type, data) {
    const errorLog = {
      type: type,
      timestamp: new Date().toISOString(),
      data: data,
      userAgent: wx.getSystemInfoSync()
    }

    console.error('[Error Log]', errorLog)
  },

  /**
   * 构建登录请求数据
   */
  buildLoginRequestData(code, encryptedData, iv, userInfo) {
    const requestData = {
      code: code
    }

    // 只有在所有参数都有值时才添加加密数据
    if (encryptedData && iv) {
      requestData.encrypted_data = encryptedData
      requestData.iv = iv
    }

    // 只有在有用户信息时才添加
    if (userInfo) {
      requestData.user_info = userInfo
    }

    console.log('[Login] 构建的请求数据:', requestData)
    return requestData
  },

  /**
   * 重置登录状态
   */
  resetLoginState() {
    this.setData({
      isLoggingIn: false,
      loginStep: 1,
      isGettingUserProfile: false,
      currentLoginCode: null,
      loginRetryCount: 0
    })
  },

  /**
   * 处理登录成功
   */
  handleLoginSuccess(userData) {
    try {
      console.log('[Login] 处理登录成功:', userData)

      // 保存用户信息到本地存储
      this.saveUserInfo(userData)

      // 更新全局用户状态
      this.updateGlobalUserState(userData)

      // 键检查用户是否为员工，如果是则同步员工登录状态
      this.syncEmployeeStatusIfNeeded(userData)

      // 跳转到相应页面
      this.redirectAfterLogin()
    } catch (error) {
      console.error('[Login] 处理登录成功时出错:', error)
      this.handleLoginError('登录处理异常，请重试')
    }
  },

  /**
   * 检查并同步员工状态（如果是员工账号）
   */
  syncEmployeeStatusIfNeeded(userData) {
    console.log('[Login] 检查用户是否为员工:', userData)

    // 检查用户类型
    const isEmployee = userData.is_staff_member ||
      userData.user_type === 'employee' ||
      userData.user_type === 'admin'

    const hasStaffId = userData.staff_id && userData.staff_id.trim() !== ''

    if (isEmployee && hasStaffId) {
      console.log('[Login] 用户是员工账号，同步员工登录状态')

      // 构建员工信息 
      const employeeInfo = {
        // 基础信息
        id: userData.id,
        username: userData.username || userData.nickname,
        nickname: userData.nickname || userData.username,
        email: userData.email || '',
        phone: userData.phone || '',
        avatar_url: userData.avatar_url || userData.avatar || '',
        avatar: userData.avatar || userData.avatar_url || '',
        gender: userData.gender || 0,

        // 员工特定信息
        real_name: userData.real_name || userData.nickname || userData.username,
        staff_id: userData.staff_id,
        employee_id: userData.employee_id || userData.id,
        department: userData.department || '未分配部门',
        position: userData.position || '未分配职位',
        user_type: userData.user_type || 'employee',

        // 状态信息
        is_staff: true,
        is_staff_member: true,
        is_verified: userData.is_verified || true,
        is_active: true,
        is_phone_bound: userData.is_phone_bound || false,
        is_wechat_bound: userData.is_wechat_bound || false,

        // 时间信息
        created_at: userData.created_at || '',
        updated_at: userData.updated_at || '',
        last_login: userData.last_login || '',
        last_login_time: userData.last_login_time || new Date().toISOString(),

        // 权限和组
        permissions: userData.permissions || [],
        groups: userData.groups || [],

        // token信息（使用普通用户的token，因为员工通道API可能也接受）
        token: userData.token || {
          access: wx.getStorageSync('token') || '',
          refresh: wx.getStorageSync('refresh_token') || ''
        }
      }

      // 保存员工信息到本地存储
      wx.setStorageSync('employeeInfo', employeeInfo)

      // 保存员工token（使用普通用户的token，后续可刷新为专用token）
      const token = wx.getStorageSync('token')
      if (token) {
        wx.setStorageSync('employeeToken', token)
        console.log('[Login] 已同步员工token')
      }

      // 保存员工刷新token
      const refreshToken = wx.getStorageSync('refresh_token')
      if (refreshToken) {
        wx.setStorageSync('employeeRefreshToken', refreshToken)
      }

      // 更新全局状态中的员工信息
      const app = getApp()
      if (app && app.globalData) {
        app.globalData.employeeInfo = employeeInfo
        app.globalData.isEmployeeLoggedIn = true
        app.globalData.employeeToken = token

        console.log('[Login] 已更新全局员工状态', {
          isEmployeeLoggedIn: app.globalData.isEmployeeLoggedIn,
          employeeName: employeeInfo.real_name
        })
      }

      console.log('[Login] 员工状态同步完成')
    } else {
      console.log('[Login] 用户不是员工账号，无需同步员工状态')

      // 如果不是员工，清理可能存在的旧员工数据
      wx.removeStorageSync('employeeToken')
      wx.removeStorageSync('employeeInfo')
      wx.removeStorageSync('employeeRefreshToken')

      // 更新全局状态
      const app = getApp()
      if (app && app.globalData) {
        app.globalData.employeeInfo = null
        app.globalData.isEmployeeLoggedIn = false
        app.globalData.employeeToken = null
      }
    }
  },


  /**
   * 保存用户信息到本地存储
   */
  saveUserInfo(userInfo) {
    try {
      // 保存完整的用户信息
      wx.setStorageSync('userInfo', userInfo)

      // 保存token
      if (userInfo.token && userInfo.token.access) {
        wx.setStorageSync('token', userInfo.token.access)
        wx.setStorageSync('refresh_token', userInfo.token.refresh)
      }

      // 保存登录状态
      wx.setStorageSync('isLogin', true)
      wx.setStorageSync('isGuest', false)
      wx.setStorageSync('loginTime', new Date().getTime())

      console.log('[Login] 用户信息保存成功')

    } catch (e) {
      console.error('[Login] 保存用户信息失败:', e)
      throw new Error('用户信息保存失败')
    }
  },

  /**
   * 更新全局用户状态
   */
  updateGlobalUserState(userInfo) {
    const app = getApp()
    if (app && app.globalData) {
      app.globalData.userInfo = userInfo
      app.globalData.isLoggedIn = true
      app.globalData.isGuest = false
      app.globalData.token = userInfo.token ? userInfo.token.access : null

      // 触发登录成功事件
      if (app.emitLoginSuccess) {
        app.emitLoginSuccess(userInfo)
      }
    }
  },

  /**
   * 登录后跳转逻辑 
   */
  redirectAfterLogin() {
    this.showSimpleToast('登录成功', 'success')

    setTimeout(() => {
      // 检查是否是从员工通道跳转过来的
      const isFromEmployeePassage = this.data.fromPage === 'employeepassage'
      const hasPageStack = this.data.pageStack && this.data.pageStack.length > 0

      // 情况1：从员工通道过来的，返回上一页
      if (isFromEmployeePassage && hasPageStack) {
        console.log('[Login] 从员工通道返回上一页')
        wx.navigateBack({
          delta: 1
        })
        return
      }

      // 情况2：有重定向URL，跳转到指定页面
      if (this.data.redirectUrl && this.data.isFromRedirect) {
        console.log('[Login] 跳转到重定向页面:', this.data.redirectUrl)

        // 处理重定向URL，确保格式正确
        let targetUrl = this.data.redirectUrl

        // 移除URL中的多余斜杠和特殊字符
        targetUrl = targetUrl.trim()

        // 如果URL以双斜杠或编码的双斜杠开头，修复它
        if (targetUrl.startsWith('//') || targetUrl.startsWith('%2F%2F')) {
          targetUrl = targetUrl.replace(/^\/\//, '').replace(/^%2F%2F/, '')
        }

        // 如果URL以单斜杠开头但不是pages，添加pages前缀
        if (targetUrl.startsWith('/') && !targetUrl.startsWith('/pages/')) {
          targetUrl = '/pages' + (targetUrl === '/' ? '/index/index' : targetUrl)
        }

        // 如果URL没有以斜杠开头，添加斜杠
        if (!targetUrl.startsWith('/')) {
          targetUrl = '/' + targetUrl
        }

        console.log('[Login] 处理后的目标URL:', targetUrl)

        // 检查是否是tab页
        const tabPages = [
          '/pages/index/index',
          '/pages/mall/index/index',
          '/pages/news/index/index',
          '/pages/user/index/index'
        ]

        // 清理目标URL，确保格式正确
        const cleanUrl = targetUrl.split('?')[0] // 移除查询参数进行判断

        if (tabPages.includes(cleanUrl)) {
          // 如果是tab页，使用switchTab
          console.log('[Login] 使用switchTab跳转到:', cleanUrl)
          wx.switchTab({
            url: cleanUrl,
            success: () => {
              console.log('[Login] 跳转到tab页成功')
            },
            fail: (err) => {
              console.error('[Login] 跳转到tab页失败:', err)
              // 尝试使用reLaunch作为后备方案
              wx.reLaunch({
                url: cleanUrl,
                fail: (reLaunchErr) => {
                  console.error('[Login] reLaunch也失败:', reLaunchErr)
                  this.redirectToDefaultPage()
                }
              })
            }
          })
        } else {
          // 如果是普通页面，使用redirectTo
          console.log('[Login] 使用redirectTo跳转到:', targetUrl)
          wx.redirectTo({
            url: targetUrl,
            success: () => {
              console.log('[Login] 跳转到重定向页面成功')
            },
            fail: (err) => {
              console.error('[Login] 跳转到重定向页面失败:', err)
              // 尝试使用navigateTo作为后备方案
              wx.navigateTo({
                url: targetUrl,
                fail: (navigateErr) => {
                  console.error('[Login] navigateTo也失败:', navigateErr)
                  // 最后尝试使用reLaunch
                  wx.reLaunch({
                    url: '/pages/index/index',
                    complete: () => {
                      console.log('[Login] 已返回到首页')
                    }
                  })
                }
              })
            }
          })
        }
      } else {
        // 情况3：没有重定向URL，跳转到默认页面
        this.redirectToDefaultPage()
      }
    }, 1500)
  },

  // URL规范化方法
  normalizeRedirectUrl(url) {
    if (!url) return '/pages/index/index'

    try {
      // 尝试解码
      let decodedUrl = decodeURIComponent(url)

      // 确保URL格式正确
      if (decodedUrl.startsWith('http')) {
        // 如果是完整URL，提取路径部分
        const urlObj = new URL(decodedUrl)
        decodedUrl = urlObj.pathname
      }

      // 确保以斜杠开头
      if (!decodedUrl.startsWith('/')) {
        decodedUrl = '/' + decodedUrl
      }

      // 确保是有效的页面路径
      if (!decodedUrl.startsWith('/pages/')) {
        decodedUrl = '/pages' + decodedUrl
      }

      return decodedUrl
    } catch (error) {
      console.error('[Login] URL规范化失败:', error)
      return '/pages/index/index'
    }
  },


  /**
   * 跳转到默认页面
   */
  redirectToDefaultPage() {
    console.log('[Login] 跳转到默认页面')
    wx.switchTab({
      url: '/pages/user/index/index',
      success: () => {
        console.log('[Login] 跳转到个人中心成功')
      },
      fail: (err) => {
        console.error('[Login] 跳转到个人中心失败:', err)
        wx.redirectTo({
          url: '/pages/user/index/index'
        })
      }
    })
  },

  /**
   * 统一的弹窗显示
   */
  showUnifiedAlert(alertConfig) {
    this.setData({
      showUnifiedAlert: true,
      unifiedAlertTitle: alertConfig.title || '提示',
      unifiedAlertContent: alertConfig.content || '',
      unifiedAlertActions: alertConfig.actions || []
    })
  },

  /**
   * 隐藏统一弹窗
   */
  hideUnifiedAlert() {
    this.setData({
      showUnifiedAlert: false
    })
  },

  /**
   * 统一的Toast提示
   */
  showSimpleToast(title, icon = 'none') {
    wx.showToast({
      title: title,
      icon: icon,
      duration: 2000
    })
  },

  /**
   * 处理统一弹窗的按钮
   */
  handleUnifiedAlertAction(e) {
    const {
      index
    } = e.currentTarget.dataset
    const action = this.data.unifiedAlertActions[index]

    if (action && action.handler) {
      action.handler()
    }
  },

  /**
   * 协议勾选
   */
  toggleAgreement() {
    const newValue = !this.data.agreementChecked
    this.setData({
      agreementChecked: newValue
    })
  },

  /**
   * 查看用户协议
   */
  showUserAgreement() {
    this.setData({
      showAgreementModal: true,
      agreementTitle: '用户协议',
      agreementContent: `欢迎使用奇奇回收服务！\n\n本协议是您与奇奇回收之间关于使用奇奇回收服务所订立的协议。\n\n1. 服务内容\n奇奇回收为您提供废旧物品回收、环保知识普及、积分兑换等服务。\n\n2. 用户账号\n您需要注册账号才能使用我们的服务。请确保提供的信息真实、准确、完整。\n\n3. 用户行为规范\n您在使用服务时应当遵守法律法规，不得从事任何违法违规行为。\n\n4. 隐私保护\n我们非常重视您的隐私，详细内容请参见《隐私政策》。\n\n5. 服务变更与终止\n我们可能根据业务需要变更、暂停或终止部分或全部服务。\n\n6. 免责声明\n在法律允许的范围内，我们对因不可抗力导致的服务中断不承担责任。\n\n7. 法律适用\n本协议的订立、执行和解释及争议的解决均适用中华人民共和国法律。\n\n8. 协议修改\n我们有权根据需要不时修改本协议，修改后的协议将在公布后生效。\n\n请您仔细阅读以上协议内容，如果您同意，请点击"同意"开始使用我们的服务。`
    })
  },

  /**
   * 查看隐私政策
   */
  showPrivacyPolicy() {
    this.setData({
      showAgreementModal: true,
      agreementTitle: '隐私政策',
      agreementContent: `奇奇回收隐私政策\n\n引言\n奇奇回收（以下简称"我们"）非常重视用户的隐私保护。本隐私政策旨在说明我们如何收集、使用、存储和保护您的个人信息。\n\n一、信息收集\n我们收集的信息包括：\n1. 您提供的信息：注册账号时提供的手机号、昵称、头像等。\n2. 设备信息：设备型号、操作系统版本、唯一设备标识符等。\n3. 日志信息：您使用服务时自动产生的日志，包括访问时间、IP地址等。\n\n二、信息使用\n我们使用您的信息用于：\n1. 提供、维护和改进我们的服务。\n2. 个性化推荐和内容展示。\n3. 安全保障和风险控制。\n4. 法律合规和争议解决。\n\n三、信息共享\n我们不会将您的个人信息出售给第三方。仅在以下情况下共享：\n1. 获得您的明确同意。\n2. 为提供您要求的服务所必需。\n3. 法律要求或政府主管部门强制要求。\n\n四、信息安全\n我们采用合理的安全措施保护您的个人信息，防止未经授权的访问、使用或泄露。\n\n五、您的权利\n您有权：\n1. 访问、更正或删除您的个人信息。\n2. 限制或反对我们处理您的信息。\n3. 撤回已同意的授权。\n\n六、儿童隐私\n我们的服务不面向儿童，不会故意收集儿童的个人信息。\n\n七、政策更新\n我们可能适时更新本政策，更新后的政策将在公布后生效。\n\n八、联系我们\n如果您对本政策有任何疑问，请通过客服渠道联系我们。\n\n感谢您阅读我们的隐私政策！`
    })
  },

  /**
   * 隐藏协议弹窗
   */
  hideAgreementModal() {
    this.setData({
      showAgreementModal: false
    })
  },

  /**
   * 手机号登录
   */
  handlePhoneLogin() {
    if (!this.data.agreementChecked) {
      this.showAgreementAlert(() => {
        wx.navigateTo({
          url: '/pages/user/auth/phone-login'
        })
      })
      return
    }
    wx.navigateTo({
      url: '/pages/user/auth/phone-login'
    })
  },

  /**
   * 员工登录  
   * 传递来源页面信息
   */
  handleEmployeeLogin() {
    if (!this.data.agreementChecked) {
      this.showAgreementAlert(() => {
        // 传递当前页面信息，以便员工登录后返回
        wx.navigateTo({
          url: '/pages/user/employeepassage/employeepassage?from=login&redirect=' + encodeURIComponent(this.data.redirectUrl || '')
        })
      })
      return
    }
    wx.navigateTo({
      url: '/pages/user/employeepassage/employeepassage?from=login&redirect=' + encodeURIComponent(this.data.redirectUrl || '')
    })
  },

  /**
   * 游客登录
   */
  handleVisitorLogin() {
    if (!this.data.agreementChecked) {
      this.showAgreementAlert(() => {
        this.executeVisitorLogin()
      })
      return
    }
    this.executeVisitorLogin()
  },

  /**
   * 显示协议提示
   */
  showAgreementAlert(callback) {
    this.showUnifiedAlert({
      title: '温馨提示',
      content: '请先阅读并同意用户协议和隐私政策',
      actions: [{
          text: '取消',
          type: 'cancel',
          handler: () => this.hideUnifiedAlert()
        },
        {
          text: '查看协议',
          type: 'primary',
          handler: () => {
            this.hideUnifiedAlert()
            this.showUserAgreement()
          }
        },
        {
          text: '同意并继续',
          type: 'confirm',
          handler: () => {
            this.hideUnifiedAlert()
            this.setData({
              agreementChecked: true
            })
            if (callback) callback()
          }
        }
      ]
    })
  },

  /**
   * 执行游客登录
   */
  executeVisitorLogin() {
    this.showUnifiedAlert({
      title: '游客模式',
      content: '游客模式下部分功能将无法使用，建议登录后体验完整功能',
      actions: [{
          text: '去登录',
          type: 'cancel',
          handler: () => this.hideUnifiedAlert()
        },
        {
          text: '继续游客模式',
          type: 'primary',
          handler: () => {
            this.hideUnifiedAlert()
            this.setGuestMode()
          }
        }
      ]
    })
  },

  /**
   * 设置游客模式
   */
  setGuestMode() {
    const app = getApp()
    if (app && app.globalData) {
      app.globalData.isGuest = true
      app.globalData.isLoggedIn = false
      app.globalData.userInfo = {
        nickname: '游客用户',
        username: 'guest_user',
        points: 0,
        avatar_url: '/static/tabbar/my-active.png'
      }
    }

    wx.setStorageSync('isGuest', true)
    wx.setStorageSync('isLogin', false)
    wx.setStorageSync('userInfo', {
      nickname: '游客用户',
      username: 'guest_user',
      points: 0,
      avatar_url: '/static/tabbar/my-active.png'
    })

    this.showSimpleToast('已进入游客模式', 'success')

    setTimeout(() => {
      // 游客模式也支持重定向
      if (this.data.redirectUrl && this.data.isFromRedirect) {
        wx.redirectTo({
          url: this.data.redirectUrl
        })
      } else {
        wx.switchTab({
          url: '/pages/user/index/index'
        })
      }
    }, 1500)
  }

})