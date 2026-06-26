// phone-login.js - 已存在，需要修改和补充
const {
  baseUrl
} = require('../../../config/settings.js')

Page({
  data: {
    phone: '',
    code: '',
    canGetCode: true,
    codeText: '获取验证码',
    countdown: 60,
    canLogin: false,
    currentTab: 'login',
    password: '',
    confirmPassword: '',
    newPassword: '',
    confirmNewPassword: '',
    canRegister: false,
    canReset: false,
    // 新增：用于区分不同表单的用途
    formPurpose: 'login' // 'login', 'register', 'forget'
  },

  onLoad(options) {
    console.log('手机号登录页面加载')
    
    // 如果从其他页面传入tab参数
    if (options.tab) {
      this.setData({
        currentTab: options.tab
      })
    }
  },

  // 手机号输入
  onPhoneInput(e) {
    const phone = e.detail.value
    this.setData({
      phone
    })
    this.checkFormStatus()
  },

  // 验证码输入
  onCodeInput(e) {
    const code = e.detail.value
    this.setData({
      code
    })
    this.checkFormStatus()
  },

  // 检查登录按钮状态
  checkLoginButton() {
    const { phone, code } = this.data
    const canLogin = phone.length === 11 && code.length === 6
    this.setData({
      canLogin
    })
  },

  // 获取验证码  
getVerifyCode() {
  const { phone, canGetCode, currentTab } = this.data

  if (!canGetCode) {
    wx.showToast({
      title: '请稍后再试',
      icon: 'none'
    })
    return
  }

  // 验证手机号格式
  if (!phone || phone.length !== 11) {
    wx.showToast({
      title: '请输入11位手机号',
      icon: 'none'
    })
    return
  }

  // 使用正则验证手机号
  const phoneRegex = /^1[3-9]\d{9}$/
  if (!phoneRegex.test(phone)) {
    wx.showToast({
      title: '手机号格式不正确',
      icon: 'none'
    })
    return
  }

  // 根据当前tab确定验证码用途
  let purpose = 'login'
  if (currentTab === 'register') {
    purpose = 'register'
  } else if (currentTab === 'forget') {
    purpose = 'reset_password'
  }

  wx.showLoading({
    title: '发送中...',
    mask: true
  })

  console.log('发送验证码请求:', {
    phone: phone,
    purpose: purpose
  })

  // 尝试不同的API端点
  const apiEndpoints = [
    baseUrl + '/user/send_sms/', // 第一种可能的端点
    baseUrl + '/user/send_sms_code/', // 第二种可能的端点
    baseUrl + '/user/send_sms/verify/', // 第三种可能的端点
    baseUrl + '/user/send-sms-code/' // 第四种可能的端点（注意横线）
  ]

  // 依次尝试每个端点
  const tryApiRequest = (index) => {
    if (index >= apiEndpoints.length) {
      wx.hideLoading()
      wx.showToast({
        title: '无法连接到服务器',
        icon: 'none'
      })
      return
    }

    const apiUrl = apiEndpoints[index]
    console.log(`尝试API端点 ${index + 1}: ${apiUrl}`)

    wx.request({
      url: apiUrl,
      method: 'POST',
      header: {
        'Content-Type': 'application/json'
      },
      data: {
        phone: phone,
        purpose: purpose
      },
      success: (res) => {
        wx.hideLoading()
        console.log('API响应状态码:', res.statusCode)
        console.log('API响应数据:', res.data)
        
        if (res.statusCode === 200 && res.data.code === 200) {
          // 成功发送验证码
          wx.showToast({
            title: '验证码已发送',
            icon: 'success'
          })
          
          // 开始倒计时
          this.startCountdown()
          
          // 开发环境：显示验证码（如果有）
          if (res.data.data && res.data.data.code) {
            console.log('✅ 验证码（开发环境）:', res.data.data.code)
            // 自动填充验证码（开发环境）
            this.setData({ 
              code: res.data.data.code,
              canLogin: true
            })
            
            // 显示开发环境提示
            setTimeout(() => {
              wx.showModal({
                title: '开发环境提示',
                content: `验证码：${res.data.data.code} \n（已自动填充）`,
                showCancel: false,
                confirmText: '知道了'
              })
            }, 1000)
          }
        } else {
          // API调用失败，尝试下一个端点
          console.warn(`API端点 ${apiUrl} 失败，尝试下一个`)
          tryApiRequest(index + 1)
        }
      },
      fail: (err) => {
        wx.hideLoading()
        console.error(`API调用失败:`, err)
        
        if (index < apiEndpoints.length - 1) {
          // 尝试下一个端点
          tryApiRequest(index + 1)
        } else {
          // 所有端点都失败
          wx.showToast({
            title: '网络错误，请检查连接',
            icon: 'none'
          })
        }
      },
      complete: () => {
        console.log(`API调用完成: ${apiUrl}`)
      }
    })
  }

  // 开始尝试第一个端点
  tryApiRequest(0)
},

  // 开始倒计时
  startCountdown() {
    this.setData({
      canGetCode: false
    })

    const timer = setInterval(() => {
      let { countdown } = this.data
      countdown--

      if (countdown <= 0) {
        clearInterval(timer)
        this.setData({
          canGetCode: true,
          codeText: '获取验证码',
          countdown: 60
        })
      } else {
        this.setData({
          codeText: `${countdown}秒后重试`,
          countdown: countdown
        })
      }
    }, 1000)
  },

  // 手机号登录 - 使用统一登录接口
  handlePhoneLogin() {
    const { phone, code, canLogin } = this.data

    if (!canLogin) return

    wx.showLoading({
      title: '登录中...',
    })

    // 使用统一登录接口
    wx.request({
      url: baseUrl + '/user/login/',
      method: 'POST',
      header: {
        'Content-Type': 'application/json'
      },
      data: {
        login_type: 'phone',
        identifier: phone,
        code: code
      },
      success: (res) => {
        wx.hideLoading()
        console.log('登录响应:', res.data)

        if (res.data.code === 200) {
          // 保存用户信息
          this.saveUserInfo(res.data.data.user || res.data.data)
          
          wx.showToast({
            title: '登录成功',
            icon: 'success'
          })

          // 延迟返回上一页
          setTimeout(() => {
            // 检查是否有重定向URL
            const pages = getCurrentPages()
            if (pages.length > 1) {
              wx.navigateBack({
                delta: 1
              })
            } else {
              wx.switchTab({
                url: '/pages/user/index/index'
              })
            }
          }, 1500)
        } else {
          wx.showToast({
            title: res.data.message || '登录失败',
            icon: 'none'
          })
        }
      },
      fail: (err) => {
        wx.hideLoading()
        console.error('登录失败:', err)
        wx.showToast({
          title: '网络错误，请重试',
          icon: 'none'
        })
      }
    })
  },

  // 保存用户信息
  saveUserInfo(userData) {
    try {
      const app = getApp()

      // 保存完整的用户信息
      wx.setStorageSync('userInfo', userData)

      // 保存token
      if (userData.token && userData.token.access) {
        wx.setStorageSync('token', userData.token.access)
        wx.setStorageSync('refresh_token', userData.token.refresh)
      }

      // 保存登录状态
      wx.setStorageSync('isLogin', true)
      wx.setStorageSync('isGuest', false)
      wx.setStorageSync('loginTime', new Date().getTime())

      // 更新全局用户信息
      if (app && app.globalData) {
        app.globalData.userInfo = userData
        app.globalData.isLoggedIn = true
        app.globalData.isGuest = false
      }

      console.log('用户信息保存成功')
    } catch (e) {
      console.error('保存用户信息失败:', e)
      wx.showToast({
        title: '保存信息失败',
        icon: 'none'
      })
    }
  },

  // 切换到微信登录
  switchToWechatLogin() {
    wx.navigateBack()
  },

  // 切换tab
  switchTab(e) {
    const tab = e.currentTarget.dataset.tab
    this.setData({
      currentTab: tab,
      phone: '',
      code: '',
      password: '',
      confirmPassword: '',
      newPassword: '',
      confirmNewPassword: ''
    })
  },

  // 密码输入
  onPasswordInput(e) {
    const password = e.detail.value
    this.setData({
      password
    })
    this.checkFormStatus()
  },

  // 确认密码输入
  onConfirmPasswordInput(e) {
    const confirmPassword = e.detail.value
    this.setData({
      confirmPassword
    })
    this.checkFormStatus()
  },

  // 新密码输入
  onNewPasswordInput(e) {
    const newPassword = e.detail.value
    this.setData({
      newPassword
    })
    this.checkFormStatus()
  },

  // 确认新密码输入
  onConfirmNewPasswordInput(e) {
    const confirmNewPassword = e.detail.value
    this.setData({
      confirmNewPassword
    })
    this.checkFormStatus()
  },

  // 检查所有表单状态
  checkFormStatus() {
    const { currentTab, phone, code, password, confirmPassword, newPassword, confirmNewPassword } = this.data
    
    let canLogin = false
    let canRegister = false
    let canReset = false

    if (currentTab === 'login') {
      canLogin = phone.length === 11 && code.length === 6
    } else if (currentTab === 'register') {
      canRegister = phone.length === 11 && code.length === 6 && 
                   password.length >= 6 && password === confirmPassword
    } else if (currentTab === 'forget') {
      canReset = phone.length === 11 && code.length === 6 && 
                newPassword.length >= 6 && newPassword === confirmNewPassword
    }

    this.setData({
      canLogin,
      canRegister,
      canReset
    })
  },

  // 处理注册
  handleRegister() {
    const { phone, code, password, canRegister } = this.data

    if (!canRegister) return

    wx.showLoading({
      title: '注册中...',
    })

    wx.request({
      url: baseUrl + '/user/register/',
      method: 'POST',
      header: {
        'Content-Type': 'application/json'
      },
      data: {
        phone,
        code,
        password,
        password_confirm: password // 前后端字段名可能需要调整
      },
      success: (res) => {
        wx.hideLoading()
        console.log('注册响应:', res.data)
        
        if (res.data.code === 200 || res.data.code === 201) {
          wx.showToast({
            title: '注册成功',
            icon: 'success'
          })
          
          // 注册成功后自动登录
          this.saveUserInfo(res.data.data || res.data.data.user)
          
          setTimeout(() => {
            // 返回上一页或跳转到首页
            const pages = getCurrentPages()
            if (pages.length > 1) {
              wx.navigateBack({
                delta: 1
              })
            } else {
              wx.switchTab({
                url: '/pages/user/index/index'
              })
            }
          }, 1500)
        } else {
          wx.showToast({
            title: res.data.message || '注册失败',
            icon: 'none'
          })
        }
      },
      fail: (err) => {
        wx.hideLoading()
        console.error('注册失败:', err)
        wx.showToast({
          title: '网络错误，请重试',
          icon: 'none'
        })
      }
    })
  },

  // 处理重置密码
  handleResetPassword() {
    const { phone, code, newPassword, canReset } = this.data

    if (!canReset) return

    wx.showLoading({
      title: '重置中...',
    })

    wx.request({
      url: baseUrl + '/user/forgot_password/',
      method: 'POST',
      header: {
        'Content-Type': 'application/json'
      },
      data: {
        phone,
        code,
        new_password: newPassword,
        confirm_password: newPassword
      },
      success: (res) => {
        wx.hideLoading()
        console.log('重置密码响应:', res.data)
        
        if (res.data.code === 200) {
          wx.showToast({
            title: '密码重置成功',
            icon: 'success'
          })
          
          // 重置成功后提示用户登录
          setTimeout(() => {
            this.setData({ 
              currentTab: 'login',
              newPassword: '',
              confirmNewPassword: ''
            })
            
            wx.showModal({
              title: '提示',
              content: '密码重置成功，请使用新密码登录',
              showCancel: false
            })
          }, 1500)
        } else {
          wx.showToast({
            title: res.data.message || '重置失败',
            icon: 'none'
          })
        }
      },
      fail: (err) => {
        wx.hideLoading()
        console.error('重置密码失败:', err)
        wx.showToast({
          title: '网络错误，请重试',
          icon: 'none'
        })
      }
    })
  },
  
  // 返回上一页
  goBack() {
    const pages = getCurrentPages()
    if (pages.length > 1) {
      wx.navigateBack({
        delta: 1
      })
    } else {
      wx.switchTab({
        url: '/pages/user/index/index'
      })
    }
  }
})