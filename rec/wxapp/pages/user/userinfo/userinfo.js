// pages/user/userinfo/userinfo.js
const app = getApp();

Page({
  data: {
    userInfo: {
      avatar: '',
      name: '',
      username: '',
      phone: '',
      employeeId: ''
    },
    originalUserInfo: {},
    smsCode: '', // 短信验证码
    smsCountdown: 0, // 倒计时
    isPhoneChanged: false // 手机号是否改变

  },

  onLoad: function () {
    console.log('userinfo页面加载');
    this.debugAuthInfo();
    this.loadUserInfo();
  },

  // 调试认证信息
  debugAuthInfo: function () {
    const token = wx.getStorageSync('token');
    const user = wx.getStorageSync('user');

    console.log('=== 认证信息调试 ===');
    console.log('Token 存在:', !!token);
    console.log('Token 值:', token);
    console.log('Token 类型:', typeof token);
    console.log('Token 长度:', token ? token.length : 0);
    console.log('User 存在:', !!user);
    console.log('Global Token:', app.globalData.token);
    console.log('Global HasLogin:', app.globalData.hasLogin);
    console.log('BaseURL:', app.globalData.baseURL);

    if (user && user.profile) {
      console.log('用户资料:', user.profile);
      console.log('头像URL:', user.profile.avatar_url);
      console.log('头像字段:', user.profile.avatar);
    }
    console.log('========================');
  },

  // 检查登录状态
  checkLoginStatus: function () {
    const token = wx.getStorageSync('token');
    const user = wx.getStorageSync('user');

    return !!(token && user);
  },

  // 加载用户信息
  loadUserInfo: function () {
    if (!this.checkLoginStatus()) {
      console.log('未登录，跳转到登录页');
      this.redirectToLogin();
      return;
    }

    const user = wx.getStorageSync('user');
    if (user) {
      console.log('从存储加载的用户数据:', user);

      // 处理头像URL
      let avatar = user.profile?.avatar_url || user.profile?.wechat_profile?.avatar_url;
      console.log('原始头像URL:', avatar);
      console.log('头像字段值:', user.profile?.avatar);

      // 开发环境下，允许使用HTTP链接
      if (avatar && avatar.startsWith('http://')) {
        console.log('开发环境使用HTTP头像链接:', avatar);
      } else if (!avatar) {
        avatar = '/static/tabbar/my-active.png';
        console.log('使用默认头像');
      }

      const userInfo = {
        avatar: avatar || '/static/tabbar/my-active.png',
        name: user.first_name && user.last_name ? `${user.first_name}${user.last_name}` : (user.profile?.wechat_profile?.nick_name || '微信用户'),
        username: user.username,
        phone: user.profile?.phone || '',
        employeeId: user.profile?.employee_id || ''
      };

      console.log('设置的用户信息:', userInfo);

      this.setData({
        userInfo: userInfo,
        originalUserInfo: {
          ...userInfo
        }
      });
    }
  },

  // 手机号输入
  onPhoneInput: function (e) {
    const newPhone = e.detail.value;
    const isChanged = newPhone !== this.data.originalUserInfo.phone;

    this.setData({
      'userInfo.phone': newPhone,
      isPhoneChanged: isChanged
    });
  },

  // 验证码输入
  onSmsCodeInput: function (e) {
    this.setData({
      smsCode: e.detail.value
    });
  },

  // 发送短信验证码
  sendSmsCode: function () {
    const that = this;
    const phone = this.data.userInfo.phone;
    const token = wx.getStorageSync('token');

    if (!phone) {
      wx.showToast({
        title: '请输入手机号',
        icon: 'none'
      });
      return;
    }

    if (!this.validatePhone(phone)) {
      wx.showToast({
        title: '手机号格式不正确',
        icon: 'none'
      });
      return;
    }

    if (!token) {
      this.handleTokenExpired('发送验证码');
      return;
    }

    wx.showLoading({
      title: '发送中...',
    });

    wx.request({
      url: app.globalData.baseURL + '/user/send_sms_code/',
      method: 'POST',
      data: {
        phone: phone
      },
      header: {
        'Authorization': 'Token ' + token,
        'content-type': 'application/json'
      },
      success: function (res) {
        wx.hideLoading();
        console.log('发送验证码响应:', res);

        if (res.statusCode === 200 && res.data.success) {
          wx.showToast({
            title: '验证码已发送',
            icon: 'success'
          });

          // 开始倒计时
          that.startCountdown();
        } else {
          wx.showToast({
            title: res.data.error || '发送失败',
            icon: 'none'
          });
        }
      },
      fail: function (error) {
        wx.hideLoading();
        wx.showToast({
          title: '网络错误',
          icon: 'none'
        });
      }
    });
  },

  // 开始倒计时
  startCountdown: function () {
    let countdown = 60;
    this.setData({
      smsCountdown: countdown
    });

    const timer = setInterval(() => {
      countdown--;
      this.setData({
        smsCountdown: countdown
      });

      if (countdown <= 0) {
        clearInterval(timer);
      }
    }, 1000);
  },

  // 修改保存资料方法
  saveProfile: function () {
    console.log('开始保存资料');
    const that = this;

    const token = wx.getStorageSync('token');

    if (!token) {
      console.log('保存资料: token 不存在');
      this.handleTokenExpired('保存资料');
      return;
    }

    const {
      userInfo,
      isPhoneChanged,
      smsCode
    } = this.data;

    // 验证手机号格式
    if (userInfo.phone && !this.validatePhone(userInfo.phone)) {
      wx.showToast({
        title: '手机号格式不正确',
        icon: 'none'
      });
      return;
    }

    // 如果手机号改变，需要验证码
    if (isPhoneChanged) {
      if (!smsCode) {
        wx.showToast({
          title: '请输入验证码',
          icon: 'none'
        });
        return;
      }

      // 调用修改手机号接口
      this.changePhoneWithVerification();
      return;
    }

    // 原有保存逻辑（非手机号修改）
    wx.showLoading({
      title: '保存中...',
    });

    const updateData = {
      profile: {
        phone: userInfo.phone,
        employee_id: userInfo.employeeId
      }
    };

    if (userInfo.name !== this.data.originalUserInfo.name) {
      updateData.first_name = userInfo.name;
    }

    console.log('发送更新数据:', updateData);
    that.trySaveProfile(updateData, 'PATCH');
  },

  // 修改手机号（带验证）
  changePhoneWithVerification: function () {
    const that = this;
    const token = wx.getStorageSync('token');
    const {
      userInfo,
      smsCode
    } = this.data;

    wx.showLoading({
      title: '修改中...',
    });

    wx.request({
      url: app.globalData.baseURL + '/user/change_phone/',
      method: 'POST',
      data: {
        new_phone: userInfo.phone,
        code: smsCode
      },
      header: {
        'Authorization': 'Token ' + token,
        'content-type': 'application/json'
      },
      success: function (res) {
        wx.hideLoading();
        console.log('修改手机号响应:', res);

        if (res.statusCode === 200 && res.data.success) {
          // 更新本地存储
          wx.setStorageSync('user', res.data.user);

          // 重置状态
          that.setData({
            smsCode: '',
            isPhoneChanged: false,
            originalUserInfo: {
              ...that.data.userInfo
            }
          });

          wx.showToast({
            title: '手机号修改成功',
            icon: 'success',
            success: () => {
              setTimeout(() => {
                wx.navigateBack();
              }, 1500);
            }
          });
        } else {
          wx.showToast({
            title: res.data.error || '修改失败',
            icon: 'none'
          });
        }
      },
      fail: function (error) {
        wx.hideLoading();
        wx.showToast({
          title: '网络错误',
          icon: 'none'
        });
      }
    });
  },

  // 验证手机号
  validatePhone: function (phone) {
    const reg = /^1[3-9]\d{9}$/;
    return reg.test(phone);
  },


  // 跳转到登录页
  redirectToLogin: function () {
    wx.redirectTo({
      url: '/pages/login/login?redirect=' + encodeURIComponent('/pages/user/userinfo/userinfo')
    });
  },

  // 返回上一页
  navBack: function () {
    wx.navigateBack({
      delta: 1
    });
  },

  // 选择头像
  chooseAvatar: function () {
    const that = this;
    wx.chooseImage({
      count: 1,
      sizeType: ['compressed'], // 压缩图片
      sourceType: ['album', 'camera'],
      success: function (res) {
        const tempFilePath = res.tempFilePaths[0];
        console.log('选择的图片路径:', tempFilePath);

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

  // 上传头像
  uploadAvatar: function (tempFilePath) {
    const that = this;
    const token = wx.getStorageSync('token');

    if (!token) {
      console.log('上传头像: token 不存在');
      this.handleTokenExpired();
      return;
    }

    console.log('开始上传头像，使用Base64方式');
    console.log('原始图片路径:', tempFilePath);

    wx.showLoading({
      title: '处理图片...',
    });

    // 压缩图片
    wx.compressImage({
      src: tempFilePath,
      quality: 80, // 压缩质量
      success: (compressRes) => {
        const compressedFilePath = compressRes.tempFilePath;
        console.log('图片压缩完成，压缩后路径:', compressedFilePath);

        // 将图片转换为 Base64
        wx.getFileSystemManager().readFile({
          filePath: compressedFilePath,
          encoding: 'base64',
          success: function (res) {
            const base64Data = res.data;
            const imageType = that.getImageType(compressedFilePath);
            const avatarData = `data:image/${imageType};base64,${base64Data}`;

            console.log('Base64转换完成，数据长度:', avatarData.length);
            console.log('Base64预览:', avatarData.substring(0, 100) + '...');

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
    return 'jpeg'; // 默认 jpeg
  },

  // 更新资料（包含头像）
  updateProfileWithAvatar: function (avatarData) {
    const that = this;
    const token = wx.getStorageSync('token');

    // 使用新的avatar_base64字段
    const updateData = {
      avatar_base64: avatarData // 直接使用Base64数据
    };

    console.log('使用PATCH方法上传头像数据，使用avatar_base64字段');
    console.log('请求数据:', updateData);

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
        console.log('头像上传完整响应:', res);

        if (res.statusCode === 200) {
          const data = res.data;
          console.log('头像上传成功，返回数据:', data);

          // 更新本地存储
          wx.setStorageSync('user', data);

          // 更新页面显示 - 使用新的头像URL
          let newAvatar = data.profile?.avatar_url;
          if (newAvatar && newAvatar.startsWith('http://')) {
            console.log('使用新的头像URL:', newAvatar);
          }

          that.setData({
            'userInfo.avatar': newAvatar || avatarData // 优先使用URL，失败则使用Base64
          });

          wx.showToast({
            title: '头像更新成功',
            icon: 'success',
            duration: 2000
          });

          // 重新加载用户信息
          setTimeout(() => {
            that.loadUserInfo();
          }, 1000);

        } else if (res.statusCode === 405) {
          console.log('头像上传: 405 - PATCH 方法不被允许');
          // 尝试 PUT 方法
          that.updateProfileWithAvatarPut(avatarData);
        } else if (res.statusCode === 401) {
          that.handleTokenExpired('头像上传');
        } else {
          let errorMsg = '上传失败';
          if (res.data && res.data.detail) {
            errorMsg = res.data.detail;
          } else if (res.data && typeof res.data === 'object') {
            // 尝试从响应数据中提取错误信息
            for (let key in res.data) {
              if (res.data[key] && res.data[key].length > 0) {
                errorMsg = res.data[key][0];
                break;
              }
            }
          }
          wx.showToast({
            title: errorMsg,
            icon: 'none'
          });
        }
      },
      fail: function (error) {
        wx.hideLoading();
        console.log('头像上传网络错误:', error);
        wx.showToast({
          title: '网络错误',
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

    console.log('尝试使用PUT方法上传头像');

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
        console.log('PUT方法头像上传完整响应:', res);

        if (res.statusCode === 200) {
          const data = res.data;
          console.log('PUT方法头像上传成功，返回数据:', data);

          // 更新本地数据 - 使用Base64数据直接显示
          that.setData({
            'userInfo.avatar': avatarData
          });

          const user = wx.getStorageSync('user');
          if (user) {
            if (!user.profile) {
              user.profile = {};
            }
            user.profile.avatar = data.profile?.avatar;
            user.profile.avatar_url = data.profile?.avatar_url;
            wx.setStorageSync('user', user);
            console.log('PUT方法更新后的本地用户数据:', user);
          }

          wx.showToast({
            title: '头像更新成功',
            icon: 'success'
          });

          // 强制重新加载用户信息
          setTimeout(() => {
            that.loadUserInfo();
          }, 1000);
        } else {
          wx.showToast({
            title: '上传失败，请稍后重试',
            icon: 'none'
          });
        }
      },
      fail: function (error) {
        wx.hideLoading();
        console.log('PUT方法头像上传网络错误:', error);
        wx.showToast({
          title: '网络错误',
          icon: 'none'
        });
      }
    });
  },

  // 输入框事件
  onNameInput: function (e) {
    this.setData({
      'userInfo.name': e.detail.value
    });
  },

  onPhoneInput: function (e) {
    this.setData({
      'userInfo.phone': e.detail.value
    });
  },

  onEmployeeIdInput: function (e) {
    this.setData({
      'userInfo.employeeId': e.detail.value
    });
  },

  // 保存资料
  saveProfile: function () {
    console.log('开始保存资料');
    const that = this;

    const token = wx.getStorageSync('token');

    if (!token) {
      console.log('保存资料: token 不存在');
      this.handleTokenExpired('保存资料');
      return;
    }

    console.log('保存资料使用的 token 长度:', token.length);

    const {
      userInfo
    } = this.data;

    // 验证手机号格式
    if (userInfo.phone && !this.validatePhone(userInfo.phone)) {
      wx.showToast({
        title: '手机号格式不正确',
        icon: 'none'
      });
      return;
    }

    wx.showLoading({
      title: '保存中...',
    });

    // 准备更新数据
    const updateData = {
      profile: {
        phone: userInfo.phone,
        employee_id: userInfo.employeeId
      }
    };

    if (userInfo.name !== this.data.originalUserInfo.name) {
      updateData.first_name = userInfo.name;
    }

    console.log('发送更新数据:', updateData);

    // 先尝试 PATCH 方法
    that.trySaveProfile(updateData, 'PATCH');
  },

  // 尝试保存资料
  trySaveProfile: function (updateData, method = 'PATCH') {
    const that = this;
    const token = wx.getStorageSync('token');

    console.log(`尝试使用 ${method} 方法保存资料`);

    wx.request({
      url: app.globalData.baseURL + '/user/me/',
      method: method,
      data: updateData,
      header: {
        'Authorization': 'Token ' + token,
        'content-type': 'application/json'
      },
      success: function (res) {
        wx.hideLoading();
        console.log('保存资料响应状态:', res.statusCode);
        console.log('保存资料完整响应:', res);

        if (res.statusCode === 200) {
          // 更新本地存储
          const user = wx.getStorageSync('user');
          if (user) {
            if (updateData.first_name) {
              user.first_name = updateData.first_name;
            }
            if (!user.profile) {
              user.profile = {};
            }
            if (user.profile) {
              user.profile.phone = updateData.profile.phone;
              user.profile.employee_id = updateData.profile.employee_id;
            }
            wx.setStorageSync('user', user);
            console.log('保存资料后的本地用户数据:', user);
          }

          wx.showToast({
            title: '保存成功',
            icon: 'success',
            success: () => {
              setTimeout(() => {
                wx.navigateBack();
              }, 1500);
            }
          });
        } else if (res.statusCode === 405) {
          console.log(`保存资料: 405 - ${method} 方法不被允许`);
          // 尝试其他方法
          if (method === 'PATCH') {
            that.trySaveProfile(updateData, 'PUT');
          } else {
            wx.showToast({
              title: '保存失败，方法不被允许',
              icon: 'none'
            });
          }
        } else if (res.statusCode === 401) {
          console.log('保存资料: 401 未授权');
          that.handleTokenExpired('保存资料');
        } else {
          let errorMsg = '保存失败';
          if (res.data && res.data.detail) {
            errorMsg = res.data.detail;
          }
          wx.showToast({
            title: errorMsg,
            icon: 'none'
          });
        }
      },
      fail: function (error) {
        wx.hideLoading();
        console.log('保存资料网络错误:', error);
        wx.showToast({
          title: '网络错误',
          icon: 'none'
        });
      }
    });
  },

  // 处理 token 过期
  handleTokenExpired: function (operation = '操作') {
    console.log(`处理 token 过期，操作: ${operation}`);

    wx.showModal({
      title: '登录已过期',
      content: `您的登录状态已过期，请重新登录（${operation}）`,
      showCancel: false,
      success: (res) => {
        if (res.confirm) {
          // 清除所有存储
          wx.removeStorageSync('token');
          wx.removeStorageSync('user');
          wx.removeStorageSync('userInfo');

          // 清除全局数据
          if (app.globalData) {
            app.globalData.userInfo = null;
            app.globalData.token = null;
            app.globalData.hasLogin = false;
          }

          // 跳转到登录页
          wx.redirectTo({
            url: '/pages/login/login'
          });
        }
      }
    });
  },

  // 验证手机号
  validatePhone: function (phone) {
    const reg = /^1[3-9]\d{9}$/;
    return reg.test(phone);
  },

  // 修改密码
  changePassword: function () {
    if (!this.checkLoginStatus()) {
      return;
    }

    wx.navigateTo({
      url: '/pages/user/change_password/change_password'
    });
  },

  // 测试 API 连接
  testAPIConnection: function () {
    const that = this;
    const token = wx.getStorageSync('token');

    if (!token) {
      wx.showToast({
        title: '请先登录',
        icon: 'none'
      });
      return;
    }

    console.log('测试 API 连接，token:', token);

    wx.request({
      url: app.globalData.baseURL + '/user/me/',
      method: 'GET',
      header: {
        'Authorization': 'Token ' + token
      },
      success: function (res) {
        console.log('API 测试响应:', res.statusCode, res.data);
        if (res.statusCode === 200) {
          wx.showToast({
            title: 'API 连接正常',
            icon: 'success'
          });
        } else {
          wx.showToast({
            title: `API 错误: ${res.statusCode}`,
            icon: 'none'
          });
        }
      },
      fail: function (error) {
        console.log('API 测试失败:', error);
        wx.showToast({
          title: 'API 连接失败',
          icon: 'none'
        });
      }
    });
  },

  // 强制刷新用户信息
  forceRefreshUserInfo: function () {
    const that = this;
    const token = wx.getStorageSync('token');

    if (!token) {
      wx.showToast({
        title: '请先登录',
        icon: 'none'
      });
      return;
    }

    wx.showLoading({
      title: '刷新中...',
    });

    wx.request({
      url: app.globalData.baseURL + '/user/me/',
      method: 'GET',
      header: {
        'Authorization': 'Token ' + token
      },
      success: function (res) {
        wx.hideLoading();
        if (res.statusCode === 200) {
          const user = res.data;
          wx.setStorageSync('user', user);
          that.loadUserInfo();
          wx.showToast({
            title: '刷新成功',
            icon: 'success'
          });
        } else {
          wx.showToast({
            title: '刷新失败',
            icon: 'none'
          });
        }
      },
      fail: function (error) {
        wx.hideLoading();
        wx.showToast({
          title: '刷新失败',
          icon: 'none'
        });
      }
    });
  }
});