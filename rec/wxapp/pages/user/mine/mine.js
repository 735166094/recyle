// pages/user/mine/mine.js
const app = getApp();

Page({
  data: {
    userInfo: null,
    isLoggedIn: false
  },

  onLoad: function () {
    this.checkLoginStatus();
  },

  onShow: function () {
    this.checkLoginStatus();
    this.loadUserInfo();
  },

  // 检查登录状态
  checkLoginStatus: function () {
    const token = wx.getStorageSync('token');
    const user = wx.getStorageSync('user');

    if (token && user) {
      this.setData({
        isLoggedIn: true
      });
      return true;
    } else {
      this.setData({
        isLoggedIn: false,
        userInfo: null
      });
      this.redirectToLogin();
      return false;
    }
  },

  // 跳转到登录页
  redirectToLogin: function () {
    wx.redirectTo({
      url: '/pages/login/login?redirect=' + encodeURIComponent('/pages/user/mine/mine')
    });
  },

  // 加载用户信息

  loadUserInfo: function () {
    /**
     * 加载并处理用户信息
     * 
     * 从本地存储中获取用户数据，处理头像URL（优先使用profile.avatar_url，其次使用wechat_profile.avatar_url），
     * 并构建包含用户信息的对象。如果用户未登录或没有存储的用户数据，则不执行任何操作。
     * 
     * 处理逻辑：
     * 1. 检查用户是否已登录，未登录则直接返回
     * 2. 从本地存储获取用户数据
     * 3. 处理头像URL（允许开发环境使用HTTP链接，否则使用默认头像）
     * 4. 构建包含头像、姓名、用户名、电话、员工ID、角色、注册时间和识别次数的用户信息对象
     * 5. 将处理后的用户信息设置到页面数据中
     * 
     * @function loadUserInfo
     * @memberof Page
     * @this {Page} 当前页面实例
     */
    if (!this.data.isLoggedIn) return;

    const user = wx.getStorageSync('user');
    if (user) {
      console.log('从存储加载的用户数据:', user);

      // 处理头像URL - 优先使用 profile.avatar_url，然后是 wechat_profile.avatar_url
      let avatar = user.profile?.avatar_url;
      console.log('原始头像URL:', avatar);

      // 如果没有头像URL，检查微信头像
      if (!avatar && user.profile?.wechat_profile?.avatar_url) {
        avatar = user.profile.wechat_profile.avatar_url;
        console.log('使用微信头像URL:', avatar);
      }

      // 开发环境下，允许使用HTTP链接
      if (avatar && avatar.startsWith('http://')) {
        console.log('开发环境使用HTTP头像链接:', avatar);
        // 在开发环境中保持HTTP链接
      } else if (!avatar) {
        avatar = '/static/tabbar/my-active.png';
        console.log('使用默认头像');
      }

      const userInfo = {
        avatar: avatar || '/static/tabbar/my-active.png',
        name: user.first_name && user.last_name ? `${user.first_name}${user.last_name}` : (user.profile?.wechat_profile?.nick_name || '微信用户'),
        username: user.username,
        phone: user.profile?.phone || '未绑定',
        employeeId: user.profile?.employee_id || '未设置',
        role: user.is_staff ? '管理员' : (user.profile?.user_type === 'employee' ? '员工' : '微信用户'),
        registerTime: user.date_joined ? new Date(user.date_joined).toLocaleDateString() : '未知',
        recognitionCount: Math.floor(Math.random() * 100) + 1
      };

      console.log('设置的用户信息:', userInfo);

      this.setData({
        userInfo: userInfo
      });
    }
  },

  // 返回上一页
  navBack: function () {
    wx.navigateBack({
      delta: 1
    });
  },

  // 编辑个人信息
  editProfile: function () {
    if (!this.checkLoginStatus()) {
      return;
    }
    wx.navigateTo({
      url: '/pages/user/userinfo/userinfo'
    });
  },

  // 选择头像
  chooseAvatar: function () {
    if (!this.checkLoginStatus()) {
      return;
    }

    const that = this;
    wx.chooseImage({
      count: 1,
      sizeType: ['compressed'],
      sourceType: ['album', 'camera'],
      success: function (res) {
        const tempFilePath = res.tempFilePaths[0];

        // 显示图片预览
        wx.previewImage({
          urls: [tempFilePath],
          success: () => {
            // 预览后询问是否使用此图片
            wx.showModal({
              title: '确认使用',
              content: '是否使用此图片作为头像？',
              success: (modalRes) => {
                if (modalRes.confirm) {
                  that.uploadAvatar(tempFilePath);
                }
              }
            });
          }
        });
      }
    });
  },

  // 上传头像 - 使用Base64方式
  uploadAvatar: function (tempFilePath) {
    const that = this;
    const token = wx.getStorageSync('token');

    if (!token) {
      this.handleTokenExpired();
      return;
    }

    console.log('开始上传头像，使用Base64方式');

    wx.showLoading({
      title: '处理图片...',
    });

    // 压缩图片
    wx.compressImage({
      src: tempFilePath,
      quality: 80,
      success: (compressRes) => {
        const compressedFilePath = compressRes.tempFilePath;

        // 将图片转换为 Base64
        wx.getFileSystemManager().readFile({
          filePath: compressedFilePath,
          encoding: 'base64',
          success: function (res) {
            const base64Data = res.data;
            const imageType = that.getImageType(compressedFilePath);
            const avatarData = `data:image/${imageType};base64,${base64Data}`;

            that.updateProfileWithAvatar(avatarData);
          },
          fail: function (error) {
            wx.hideLoading();
            console.log('读取图片文件失败:', error);
            wx.showToast({
              title: '图片处理失败',
              icon: 'none'
            });
          }
        });
      },
      fail: (error) => {
        wx.hideLoading();
        console.log('图片压缩失败:', error);
        wx.showToast({
          title: '图片处理失败',
          icon: 'none'
        });
      }
    });
  },

  // 获取图片类型
  getImageType: function (filePath) {
    const ext = filePath.split('.').pop().toLowerCase();
    if (ext === 'png') return 'png';
    if (ext === 'gif') return 'gif';
    return 'jpeg';
  },

  // 更新资料（包含头像）
  updateProfileWithAvatar: function (avatarData) {
    const that = this;
    const token = wx.getStorageSync('token');

    const updateData = {
      avatar_base64: avatarData // 使用新的avatar_base64字段
    };

    wx.request({
      url: app.globalData.baseURL + '/user/me/',
      method: 'PATCH',
      data: updateData,
      header: {
        'Authorization': 'Token ' + token,
        'content-type': 'application/json'
      },
      success: function (res) {
        wx.hideLoading();
        console.log('头像上传响应状态:', res.statusCode);

        if (res.statusCode === 200) {
          // 更新本地存储
          wx.setStorageSync('user', res.data);

          // 重新加载用户信息
          that.loadUserInfo();

          wx.showToast({
            title: '头像更新成功',
            icon: 'success'
          });
        } else if (res.statusCode === 405) {
          console.log('头像上传: 405 - PATCH 方法不被允许');
          that.updateProfileWithAvatarPut(avatarData);
        } else if (res.statusCode === 401) {
          that.handleTokenExpired();
        } else {
          wx.showToast({
            title: '上传失败',
            icon: 'none'
          });
        }
      },
      fail: function (error) {
        wx.hideLoading();
        wx.showToast({
          title: '上传失败',
          icon: 'none'
        });
      }
    });
  },

  // 使用 PUT 方法更新资料
  updateProfileWithAvatarPut: function (avatarData) {
    const that = this;
    const token = wx.getStorageSync('token');

    const updateData = {
      profile: {
        avatar: avatarData
      }
    };

    wx.request({
      url: app.globalData.baseURL + '/user/me/',
      method: 'PUT',
      data: updateData,
      header: {
        'Authorization': 'Token ' + token,
        'content-type': 'application/json'
      },
      success: function (res) {
        wx.hideLoading();
        console.log('PUT方法头像上传响应状态:', res.statusCode);

        if (res.statusCode === 200) {
          // 重新加载用户信息
          that.loadUserInfo();

          wx.showToast({
            title: '头像更新成功',
            icon: 'success'
          });
        } else {
          wx.showToast({
            title: '上传失败，请稍后重试',
            icon: 'none'
          });
        }
      },
      fail: function (error) {
        wx.hideLoading();
        wx.showToast({
          title: '上传失败',
          icon: 'none'
        });
      }
    });
  },

  // 处理 token 过期
  handleTokenExpired: function () {
    wx.showModal({
      title: '登录已过期',
      content: '您的登录状态已过期，请重新登录',
      showCancel: false,
      success: (res) => {
        if (res.confirm) {
          this.logout();
        }
      }
    });
  },

  // 绑定微信
  bindWechat: function () {
    wx.showToast({
      title: '已绑定当前微信',
      icon: 'success'
    });
  },

  // 退出登录
  logout: function () {
    const that = this;
    wx.showModal({
      title: '确认退出',
      content: '确定要退出当前账号吗？',
      confirmText: '退出',
      cancelText: '取消',
      success: function (res) {
        if (res.confirm) {
          // 清除本地存储
          wx.removeStorageSync('token');
          wx.removeStorageSync('user');
          wx.removeStorageSync('userInfo');

          // 清除全局数据
          app.globalData.userInfo = null;
          app.globalData.token = null;
          app.globalData.hasLogin = false;

          wx.showToast({
            title: '已退出登录',
            icon: 'success',
            duration: 1500,
            success: () => {
              setTimeout(() => {
                wx.redirectTo({
                  url: '/pages/login/login'
                });
              }, 1500);
            }
          });
        }
      }
    });
  },


  // 下拉刷新
  onPullDownRefresh: function () {
    console.log('触发下拉刷新');
    this.refreshUserInfo();
  },

  // 刷新用户信息
  refreshUserInfo: function () {
    const that = this;
    const token = wx.getStorageSync('token');

    if (!token) {
      wx.stopPullDownRefresh();
      return;
    }

    console.log('开始刷新用户信息');

    wx.request({
      url: app.globalData.baseURL + '/user/me/',
      method: 'GET',
      header: {
        'Authorization': 'Token ' + token
      },
      success: function (res) {
        console.log('刷新用户信息响应:', res.statusCode);

        if (res.statusCode === 200) {
          const user = res.data;
          // 更新本地存储
          wx.setStorageSync('user', user);

          // 重新加载用户信息
          that.loadUserInfo();

          wx.showToast({
            title: '刷新成功',
            icon: 'success',
            duration: 1000
          });
        } else {
          wx.showToast({
            title: '刷新失败',
            icon: 'none'
          });
        }
      },
      fail: function (error) {
        console.log('刷新用户信息失败:', error);
        wx.showToast({
          title: '网络错误',
          icon: 'none'
        });
      },
      complete: function () {
        // 停止下拉刷新
        wx.stopPullDownRefresh();
      }
    });
  },
});