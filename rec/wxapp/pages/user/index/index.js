// pages/user/index/index.js
const app = getApp()
const settings = require('../../../config/settings')

Page({

  /**
   * 页面的初始数据
   */
  data: {
    userInfo: null,
    username: '未登录',
    isLogin: false,
    isGuest: false,
    phone: '',
    points: 0,
    avatarUrl: ' ',
    isLoading: false,
    lastUpdateTime: null,
    showShare: false,
    shareCardStyle: {},
    pendingRecycleCount: 0 // 待回收订单数量
  },

  /**
   * 生命周期函数--监听页面加载
   */
  onLoad(options) {
    // 将settings保存到data中
    this.setData({
      settings: settings
    })
  },


  /**
   * 生命周期函数--监听页面初次渲染完成
   */
  onReady() {

  },

  /**
   * 生命周期函数--监听页面显示
   */
  onShow() {
    this.checkLoginStatus()
    this.loadUserInfo()
    this.checkTokenValidity()
    // 加载待评估订单数量
    this.loadPendingRecycleCount()
  },

  /**
   * 加载待评估订单数量
   */
  loadPendingRecycleCount() {
    if (!this.data.isLogin && !this.data.isGuest) {
      console.log('用户未登录，跳过加载待评估订单数量')
      return
    }

    const token = wx.getStorageSync('token')
    if (!token) {
      console.log('未找到token，无法加载待评估订单数量')
      return
    }

    // console.log('开始加载待评估订单数量')

    // 获取当前配置
    const config = this.settings || settings
    if (!config) {
      console.error('配置未加载')
      return
    }

    // 使用正确的API路径
    const apiUrl = config.scrapCarRecords || `${config.baseUrl || ''}/recycle/scrap_cars/`

    if (!apiUrl) {
      console.error('未找到API路径')
      return
    }

    // console.log('使用API路径:', apiUrl)

    wx.request({
      url: apiUrl,
      method: 'GET',
      header: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      data: {
        page: 1,
        page_size: 10,
        status: 'pending' // 筛选待评估状态的订单
      },
      success: (res) => {
        // console.log('待评估订单数量响应:', res)

        if (res.statusCode === 200 && res.data) {
          let pendingCount = 0

          // 首先检查是否有统计信息
          if (res.data.status_stats && res.data.status_stats.pending_count !== undefined) {
            // 如果有统计信息，直接获取待评估数量
            pendingCount = res.data.status_stats.pending_count || 0
            // console.log('从status_stats获取待评估数量:', pendingCount)
          } else if (res.data.count !== undefined) {
            // 如果返回了分页的count，使用count
            pendingCount = res.data.count || 0
            console.log('从count获取待评估数量:', pendingCount)
          } else if (Array.isArray(res.data.results)) {
            // 如果是分页格式的结果数组
            pendingCount = res.data.results.length || 0
            console.log('从results数组长度获取待评估数量:', pendingCount)
          } else if (Array.isArray(res.data)) {
            // 如果是数组，直接获取数组长度
            pendingCount = res.data.length || 0
            console.log('从数组长度获取待评估数量:', pendingCount)
          }

          this.setData({
            pendingRecycleCount: pendingCount
          })

          // console.log('待评估订单数量已更新:', pendingCount)
        } else {
          console.error('获取待评估订单数量失败，状态码:', res.statusCode)
          // 设置默认值
          this.setData({
            pendingRecycleCount: 0
          })
        }
      },
      fail: (err) => {
        console.error('请求待评估订单数量失败:', err)
        // 设置默认值
        this.setData({
          pendingRecycleCount: 0
        })
      }
    })
  },

  /**
   * 跳转到我的回收记录
   */
  gotoMyRecycle() {
    if (!this.data.isLogin) {
      this.showLoginAlert();
      return;
    }

    // 跳转到回收记录页面
    wx.navigateTo({
      url: '/pages/recycle/record/record',
      success: () => {
        // 成功跳转后，我们可以尝试通过页面间通信的方式传递状态
        setTimeout(() => {
          // 获取页面栈
          const pages = getCurrentPages();
          const currentPage = pages[pages.length - 1];

          // 检查是否是目标页面
          if (currentPage.route === 'pages/recycle/record/record') {
            // 直接调用record页面的筛选方法
            if (currentPage.filterByStatus) {
              currentPage.filterByStatus({
                currentTarget: {
                  dataset: {
                    status: 'pending'
                  }
                }
              });
            } else {
              // 如果直接调用失败，通过设置data的方式
              currentPage.setData({
                currentFilter: 'pending'
              });
              // 然后手动触发筛选逻辑
              if (currentPage.loadCarRecords) {
                currentPage.setData({
                  page: 1,
                  carRecords: [],
                  filteredCars: [],
                  hasMore: true,
                  isRefreshing: true
                }, () => {
                  if (currentPage.data.isLoggedIn) {
                    currentPage.loadCarRecords(() => {
                      currentPage.setData({
                        isRefreshing: false
                      });
                    });
                  } else {
                    if (currentPage.applyFilter) {
                      currentPage.applyFilter();
                    }
                    currentPage.setData({
                      isRefreshing: false
                    });
                  }
                });
              }
            }
          }
        });
      },
      fail: (err) => {
        console.error('跳转到回收记录页面失败:', err);
        wx.showToast({
          title: '跳转失败',
          icon: 'none'
        });
      }
    });
  },

  // 跳转到我的订单
  gotoMyOrders() {
    if (!this.data.isLogin) {
      this.showLoginAlert()
      return
    }
    wx.navigateTo({
      url: '/pages/recycle/record/record',
      fail: () => wx.showToast({
        title: '跳转失败',
        icon: 'none'
      })
    })
  },

  /**
   * 检查登录状态
   */
  checkLoginStatus() {
    const isLogin = wx.getStorageSync('isLogin') || false
    const isGuest = wx.getStorageSync('isGuest') || false

    console.log('登录状态检查:', {
      isLogin,
      isGuest
    })

    this.setData({
      isLogin: isLogin,
      isGuest: isGuest
    })

    // 如果未登录且不是游客，跳转到登录页
    if (!isLogin && !isGuest) {
      console.log('未登录，跳转到登录页')
      const currentPage = '/pages/user/index/index'
      wx.redirectTo({
        url: `/pages/user/login/login?redirect=${encodeURIComponent(currentPage)}`
      })
      return
    }
  },

  /**
   * 检查token有效性
   */
  checkTokenValidity() {
    const token = wx.getStorageSync('token')
    const loginTime = wx.getStorageSync('loginTime')

    if (!token || !loginTime) {
      return
    }

    // 检查token是否过期（假设7天过期）
    const now = new Date().getTime()
    const tokenAge = now - loginTime
    const sevenDays = 7 * 24 * 60 * 60 * 1000

    if (tokenAge > sevenDays) {
      console.log('Token可能已过期，建议重新登录')
      this.showTokenExpiredAlert()
    }
  },

  /**
   * 显示token过期提示
   */
  showTokenExpiredAlert() {
    wx.showModal({
      title: '登录状态过期',
      content: '您的登录状态已过期，需要重新登录',
      confirmText: '重新登录',
      cancelText: '稍后',
      success: (res) => {
        if (res.confirm) {
          this.logout()
        }
      }
    })
  },

  /**
   * 加载用户信息
   */
  loadUserInfo() {
/**
 * 加载用户信息
 * 1. 首先检查是否正在加载中，避免重复请求
 * 2. 尝试从本地缓存获取用户信息
 * 3. 如果缓存存在则更新界面，否则从服务器获取
 * 4. 最后更新加载状态和最后更新时间
 */
    if (this.data.isLoading) {
      return
    }

    this.setData({
      isLoading: true
    })

    const userInfo = wx.getStorageSync('userInfo')
    console.log('从缓存加载用户信息:', userInfo) // 这里可以查看

    if (userInfo) {
      this.updateUserInfo(userInfo)
    } else {
      console.log('未找到缓存，从服务器获取用户信息')
      this.fetchUserInfoFromServer()
    }

    this.setData({
      isLoading: false,
      lastUpdateTime: new Date().toISOString()
    })
  },

  // 在 updateUserInfo 方法中
  updateUserInfo(userInfo) {
    if (!userInfo) return

    console.log('更新用户信息:', userInfo) // 这里可以查看

    // 优先显示昵称，如果没有昵称则显示用户名
    const displayName = userInfo.nickname || userInfo.username || '微信用户'

    // 处理手机号显示（脱敏处理）
    let phoneDisplay = ''
    if (userInfo.phone) {
      phoneDisplay = userInfo.phone.replace(/(\d{3})\d{4}(\d{4})/, '$1****$2')
    }

    // 处理头像URL
    const avatarUrl = userInfo.avatar_url || '/static/tabbar/my-active.png'

    this.setData({
      userInfo: userInfo,
      username: displayName,
      phone: phoneDisplay,
      points: userInfo.points || 0,
      avatarUrl: avatarUrl
    })

    // 更新全局数据
    const app = getApp()
    if (app && app.globalData) {
      app.globalData.userInfo = userInfo
    }
  },

  /**
   * 从服务器获取用户信息
   */
  fetchUserInfoFromServer() {
    const token = wx.getStorageSync('token')
    if (!token) {
      console.log('未找到token，无法从服务器获取用户信息')
      return
    }

    wx.showLoading({
      title: '加载中...',
    })

    wx.request({
      url: this.settings.userProfile,
      method: 'GET',
      header: {
        'Authorization': `Bearer ${token}`
      },
      success: (res) => {
        wx.hideLoading()

        if (res.statusCode === 200 && res.data.code === 200) {
          console.log('从服务器获取用户信息成功:', res.data.data)
          this.updateUserInfo(res.data.data)
          wx.setStorageSync('userInfo', res.data.data)
        } else {
          console.error('获取用户信息失败:', res.data)
          if (res.statusCode === 401) {
            this.showTokenExpiredAlert()
          }
        }
      },
      fail: (err) => {
        wx.hideLoading()
        console.error('请求用户信息失败:', err)
        wx.showToast({
          title: '网络错误',
          icon: 'none'
        })
      }
    })
  },

  /**
   * 更新用户信息到页面
   */
  updateUserInfo(userInfo) {
    if (!userInfo) return

    // 优先显示昵称，如果没有昵称则显示用户名
    const displayName = userInfo.nickname || userInfo.username || '微信用户'

    // 处理手机号显示（脱敏处理）
    let phoneDisplay = ''
    if (userInfo.phone) {
      phoneDisplay = userInfo.phone.replace(/(\d{3})\d{4}(\d{4})/, '$1****$2')
    }

    // 处理头像URL
    const avatarUrl = userInfo.avatar_url || '/static/tabbar/my-active.png'

    this.setData({
      userInfo: userInfo,
      username: displayName,
      phone: phoneDisplay,
      points: userInfo.points || 0,
      avatarUrl: avatarUrl
    })

    // 更新全局数据
    const app = getApp()
    if (app && app.globalData) {
      app.globalData.userInfo = userInfo
    }
  },

  /**
   * 刷新用户信息
   */
  refreshUserInfo() {
    console.log('手动刷新用户信息')
    this.fetchUserInfoFromServer()
  },

  /**
   * 绑定手机号
   */
  bindPhoneNumber() {
    if (!this.data.isLogin) {
      wx.showToast({
        title: '请先登录',
        icon: 'none'
      })
      return
    }

    wx.showModal({
      title: '绑定手机号',
      content: '绑定手机号可以享受更多服务，是否立即绑定？',
      confirmText: '立即绑定',
      cancelText: '暂不绑定',
      success: (res) => {
        if (res.confirm) {
          // 跳转到手机号绑定页面
          wx.navigateTo({
            url: '/pages/user/auth/bind-phone',
            fail: () => {
              wx.showToast({
                title: '页面跳转失败',
                icon: 'none'
              })
            }
          })
        }
      }
    })
  },

  /**
   * 退出登录
   */
  logout() {
    wx.showModal({
      title: '确认退出',
      content: '确定要退出登录吗？',
      success: (res) => {
        if (res.confirm) {
          wx.showLoading({
            title: '退出中...',
          })

          const token = wx.getStorageSync('token')

          // 调用后端退出接口
          if (token) {
            // 使用data中的settings
            const config = this.data.settings
            if (!config || !config.userLogout) {
              console.error('配置未加载或找不到userLogout API')
              this.clearLocalStorage()
              return
            }

            wx.request({
              url: config.userLogout, // 使用config
              method: 'POST',
              header: {
                'Authorization': `Bearer ${token}`
              },
              complete: () => {
                this.clearLocalStorage()
              },
              fail: (err) => {
                console.error('调用logout API失败:', err)
                this.clearLocalStorage()
              }
            })
          } else {
            this.clearLocalStorage()
          }
        }
      }
    })
  },


  /**
   * 清除本地存储
   */
  clearLocalStorage() {
    // 清除本地存储
    wx.clearStorage()

    // 更新全局数据
    const app = getApp()
    if (app && app.globalData) {
      app.globalData.userInfo = null
      app.globalData.isLoggedIn = false
      app.globalData.isGuest = false
      app.globalData.token = null
    }

    wx.hideLoading()

    // 跳转到登录页
    wx.redirectTo({
      url: '/pages/user/login/login'
    })
  },

  /**
   * 页面相关事件处理函数--监听用户下拉动作
   */
  onPullDownRefresh() {
    console.log('下拉刷新')
    this.refreshUserInfo()
    // 重新加载待评估订单数量
    this.loadPendingRecycleCount()
    wx.stopPullDownRefresh()
  },

  /**
   * 页面上拉触底事件的处理函数
   */
  onReachBottom() {
    // 可以在这里加载更多数据
  },

  /**
   * 分享应用功能相关方法
   */

  // 显示分享卡片
  showShareCard() {
    // 创建动画实例
    const animation = wx.createAnimation({
      duration: 300,
      timingFunction: 'ease-out'
    })

    this.animation = animation
    // 先下移再上移，实现弹出效果
    animation.translateY(500).step()
    this.setData({
      showShare: true,
      shareCardStyle: animation.export()
    })

    setTimeout(() => {
      animation.translateY(0).step()
      this.setData({
        shareCardStyle: animation.export()
      })
    }, 10)
  },

  // 隐藏分享卡片
  hideShareCard() {
    const animation = wx.createAnimation({
      duration: 300,
      timingFunction: 'ease-in'
    })

    this.animation = animation
    animation.translateY(500).step()
    this.setData({
      shareCardStyle: animation.export()
    })

    setTimeout(() => {
      this.setData({
        showShare: false
      })
    }, 300)
  },

  // 分享给微信好友
  shareToFriend() {
    this.hideShareCard()

    // 直接引导用户分享
    wx.showModal({
      title: '分享给好友',
      content: '请点击页面右上角的 "···" 按钮，然后选择 "转发" 或 "发送给朋友"',
      showCancel: false,
      confirmText: '知道了'
    })
  },

  // 分享到朋友圈
  shareToTimeline() {
    this.hideShareCard()

    // 检查是否支持分享到朋友圈
    wx.showShareMenu({
      withShareTicket: true,
      menus: ['shareAppMessage', 'shareTimeline']
    }).then(() => {
      // 提示用户
      wx.showModal({
        title: '分享到朋友圈',
        content: '请点击页面右上角的 "···" 按钮，然后选择 "分享到朋友圈"',
        showCancel: false,
        confirmText: '知道了'
      })
    }).catch(() => {
      wx.showToast({
        title: '当前版本不支持朋友圈分享',
        icon: 'none'
      })
    })
  },

  // 生成分享海报
  saveShareImage() {
    this.hideShareCard()

    // 跳转到分享海报生成页面
    wx.navigateTo({
      url: '/pages/user/share/share',
      fail: () => {
        // 如果页面不存在，显示提示
        wx.showModal({
          title: '功能提示',
          content: '海报生成功能正在开发中，敬请期待！',
          showCancel: false,
          confirmText: '知道了'
        })
      }
    })
  },

  // 复制邀请链接
  copyShareLink() {
    this.hideShareCard()

    // 生成邀请链接（这里使用小程序的页面路径）
    let shareLink = '/pages/index/index'

    // 如果用户已登录，可以带上邀请码
    const userInfo = this.data.userInfo
    if (userInfo && userInfo.invite_code) {
      shareLink = `/pages/index/index?invite_code=${userInfo.invite_code}`
    }

    // 复制到剪贴板
    wx.setClipboardData({
      data: shareLink,
      success: () => {
        wx.showToast({
          title: '链接已复制',
          icon: 'success'
        })
      }
    })
  },

  // 分享给QQ好友（小程序不支持直接分享到QQ，这里留空或提示）
  shareToQQ() {
    this.hideShareCard()
    wx.showToast({
      title: '暂不支持QQ分享',
      icon: 'none'
    })
  },

  // 用户点击右上角分享（提供给微信菜单使用）
  onShareAppMessage() {
    return {
      title: this.getShareTitle(),
      path: this.getSharePath(),
      imageUrl: this.getShareImage(),
      success: (res) => {
        console.log('分享成功:', res)
        this.logShareAction('friend')
      },
      fail: (err) => {
        console.error('分享失败:', err)
      }
    }
  },

  // 分享到朋友圈（提供给微信菜单使用）
  onShareTimeline() {
    return {
      title: this.getShareTitle(),
      query: '',
      imageUrl: this.getShareImage()
    }
  },

  // 获取分享标题
  getShareTitle() {
    const userInfo = this.data.userInfo
    let title = '奇奇回收 - 环保回收，变废为宝'

    if (userInfo && userInfo.nickname) {
      title = `${userInfo.nickname} 邀请你使用奇奇回收`
    }

    return title
  },

  // 获取分享路径
  getSharePath() {
    const userInfo = this.data.userInfo
    let path = '/pages/index/index'

    // 如果用户已登录，可以带上邀请码
    if (userInfo && userInfo.invite_code) {
      path = `/pages/index/index?invite_code=${userInfo.invite_code}`
    }

    return path
  },

  // 获取分享图片
  getShareImage() {
    return '/static/img/logo.png'
  },

  // 记录分享行为（用于统计）
  logShareAction(shareType) {
    console.log('用户进行了分享:', shareType)
    // 这里可以记录分享数据，或者给用户积分奖励等
  },


  // 跳转到员工通道
  gotoEmployeePassage() {
    if (!this.data.isLogin) {
      this.showLoginAlert()
      return
    }
    wx.navigateTo({
      url: '/pages/user/employeepassage/employeepassage',
      fail: () => wx.showToast({
        title: '跳转失败',
        icon: 'none'
      })
    })
  },

  // 跳转到回收记录
  gotoRecycleRecords() {
    if (!this.data.isLogin) {
      this.showLoginAlert()
      return
    }
    wx.navigateTo({
      url: '/pages/recycle/record/record',
      fail: () => wx.showToast({
        title: '跳转失败',
        icon: 'none'
      })
    })
  },

  // 跳转到我的订单
  gotoMyOrders() {
    if (!this.data.isLogin) {
      this.showLoginAlert()
      return
    }
    wx.navigateTo({
      url: '/pages/recycle/record/record',
      fail: () => wx.showToast({
        title: '跳转失败',
        icon: 'none'
      })
    })
  },

  // 跳转到我的收藏
  gotoFavorites() {
    if (!this.data.isLogin) {
      this.showLoginAlert()
      return
    }
    wx.navigateTo({
      url: '/pages/mall/favorites/favorites',
      fail: () => wx.showToast({
        title: '跳转失败',
        icon: 'none'
      })
    })
  },

  // 跳转到积分中心
  gotoPoints() {
    if (!this.data.isLogin) {
      this.showLoginAlert()
      return
    }
    wx.navigateTo({
      url: '/pages/points/index/index',
      fail: () => wx.showToast({
        title: '积分中心暂未开放，敬请期待',
        icon: 'error'
      })
    })
  },

  // 跳转到优惠券
  gotoCoupon() {
    if (!this.data.isLogin) {
      this.showLoginAlert()
      return
    }
    wx.navigateTo({
      url: '/pages/mall/coupon/coupon',
      fail: () => wx.showToast({
        title: '跳转失败',
        icon: 'none'
      })
    })
  },

  // 跳转到地址管理
  gotoAddress() {
    if (!this.data.isLogin) {
      this.showLoginAlert()
      return
    }
    wx.navigateTo({
      url: '/pages/user/address/address',
      fail: () => wx.showToast({
        title: '跳转失败',
        icon: 'none'
      })
    })
  },

  // 跳转到系统设置
  gotoSysSettings() {
    wx.navigateTo({
      url: '/pages/user/setting/setting',
      fail: () => wx.showToast({
        title: '跳转失败',
        icon: 'none'
      })
    })
  },

  // 跳转到关于我们
  gotoAboutOurs() {
    wx.navigateTo({
      url: '/pages/user/aboutour/aboutour',
      fail: () => wx.showToast({
        title: '跳转失败',
        icon: 'none'
      })
    })
  },

  // 跳转到客服中心
  goToCustomerService() {
    wx.showModal({
      title: '客服中心',
      content: '客服热线：0553-5922400\n 工作时间：8:30-17:00',
      confirmText: '拨打热线',
      cancelText: '取消',
      success: (res) => {
        if (res.confirm) {
          wx.makePhoneCall({
            phoneNumber: '05535922400'
          })
        }
      }
    })
  },

  // 跳转到帮助中心
  goToHelpCenter() {
    wx.navigateTo({
      url: '/pages/user/help/help',
      fail: () => {
        wx.showToast({
          title: '帮助中心页面开发中',
          icon: 'none'
        })
      }
    })
  },

  // 显示登录提示
  showLoginAlert() {
    const currentPage = '/pages/user/index/index'
    wx.showModal({
      title: '提示',
      content: '此功能需要登录后才能使用',
      confirmText: '去登录',
      cancelText: '取消',
      success: (res) => {
        if (res.confirm) {
          wx.navigateTo({
            url: `/pages/user/login/login?redirect=${encodeURIComponent(currentPage)}`
          })
        }
      }
    })
  },

  /**
   * 生命周期函数--监听页面隐藏
   */
  onHide() {
    console.log('[UserIndex] 页面隐藏')
  },

  /**
   * 生命周期函数--监听页面卸载
   */
  onUnload() {
    console.log('[UserIndex] 页面卸载')
  }
})