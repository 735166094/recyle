// pages/user/change_password/change_password.js
const app = getApp();

Page({
  data: {
    oldPassword: '',
    newPassword: '',
    newPasswordConfirm: '',
    // 显示/隐藏密码状态
    showOldPassword: false,
    showNewPassword: false,
    showNewPasswordConfirm: false,
    // 密码匹配状态
    passwordMatchError: false,
    // 密码验证错误信息
    passwordValidationError: '',
    passwordStrength: {
      level: 0,
      text: ' ',
      length: false,
      hasUpper: false,
      hasLower: false,
      hasNumber: false,
      hasSpecial: false
    },
    strengthClass: '',
    canSubmit: false
  },

  onLoad: function (options) {
    console.log('修改密码页面加载');
  },

  // 返回上一页
  navBack: function () {
    wx.navigateBack({
      delta: 1
    });
  },

  // 切换旧密码显示/隐藏
  toggleOldPasswordVisibility: function () {
    this.setData({
      showOldPassword: !this.data.showOldPassword
    });
  },

  // 切换新密码显示/隐藏
  toggleNewPasswordVisibility: function () {
    this.setData({
      showNewPassword: !this.data.showNewPassword
    });
  },

  // 切换确认密码显示/隐藏
  toggleNewPasswordConfirmVisibility: function () {
    this.setData({
      showNewPasswordConfirm: !this.data.showNewPasswordConfirm
    });
  },

  // 输入旧密码
  onOldPasswordInput: function (e) {
    this.setData({
      oldPassword: e.detail.value,
      passwordValidationError: '' // 清除验证错误
    });
    this.validateForm();
  },

  // 输入新密码
  onNewPasswordInput: function (e) {
    const newPassword = e.detail.value;
    this.setData({
      newPassword: newPassword,
      passwordValidationError: '' // 清除验证错误
    });
    this.checkPasswordStrength(newPassword);
    this.checkPasswordMatch(); // 检查密码匹配
    this.validatePasswordRules(newPassword); // 验证密码规则
    this.validateForm();
  },

  // 输入确认新密码
  onNewPasswordConfirmInput: function (e) {
    const newPasswordConfirm = e.detail.value;
    this.setData({
      newPasswordConfirm: newPasswordConfirm,
      passwordValidationError: '' // 清除验证错误
    });
    this.checkPasswordMatch(); // 检查密码匹配
    this.validateForm();
  },

  // 检查密码是否匹配
  checkPasswordMatch: function () {
    const {
      newPassword,
      newPasswordConfirm
    } = this.data;

    // 只有当两个密码都不为空时才检查匹配
    if (newPassword && newPasswordConfirm) {
      const isMatch = newPassword === newPasswordConfirm;
      this.setData({
        passwordMatchError: !isMatch
      });
    } else {
      // 如果任一密码为空，隐藏错误提示
      this.setData({
        passwordMatchError: false
      });
    }
  },

  // 验证密码规则
  validatePasswordRules: function (password) {
    if (!password || password.length < 6) {
      return;
    }

    // 检查连续重复字符（如1111, aaaa等）
    const repeatingRegex = /(.)\1{3,}/;
    if (repeatingRegex.test(password)) {
      this.setData({
        passwordValidationError: '密码不能包含连续重复的字符'
      });
      return;
    }

    // 检查连续数字序列（如1234, 4321等）
    if (/^\d+$/.test(password)) { // 只有数字时才检查
      for (let i = 0; i <= password.length - 4; i++) {
        const segment = password.substring(i, i + 4);
        if (this.isSequentialNumbers(segment)) {
          this.setData({
            passwordValidationError: '密码不能是连续的数值'
          });
          return;
        }
      }
    }

    // 清除验证错误
    this.setData({
      passwordValidationError: ''
    });
  },

  // 检查是否为连续数字
  isSequentialNumbers: function (str) {
    if (str.length < 4) return false;

    // 检查递增序列
    let isAscending = true;
    for (let i = 1; i < str.length; i++) {
      if (parseInt(str[i]) !== parseInt(str[i - 1]) + 1) {
        isAscending = false;
        break;
      }
    }

    // 检查递减序列
    let isDescending = true;
    for (let i = 1; i < str.length; i++) {
      if (parseInt(str[i]) !== parseInt(str[i - 1]) - 1) {
        isDescending = false;
        break;
      }
    }

    return isAscending || isDescending;
  },

  // 检查密码强度
  checkPasswordStrength: function (password) {
    const strength = {
      level: 0,
      text: ' ',
      length: password.length >= 6,
      hasUpper: /[A-Z]/.test(password),
      hasLower: /[a-z]/.test(password),
      hasNumber: /[0-9]/.test(password),
      hasSpecial: /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password)
    };

    // 计算强度等级
    let score = 0;
    if (strength.length) score += 1;
    if (strength.hasUpper) score += 1;
    if (strength.hasLower) score += 1;
    if (strength.hasNumber) score += 1;
    if (strength.hasSpecial) score += 1;

    // 设置强度等级和显示文本
    let level = 0;
    let text = ' ';
    let strengthClass = '';

    if (score <= 1) {
      level = 1;
      text = '弱';
      strengthClass = 'weak';
    } else if (score <= 3) {
      level = 2;
      text = '中';
      strengthClass = 'medium';
    } else if (score <= 4) {
      level = 3;
      text = '强';
      strengthClass = 'strong';
    } else {
      level = 4;
      text = '很强';
      strengthClass = 'very-strong';
    }

    strength.level = level;
    strength.text = text;

    this.setData({
      passwordStrength: strength,
      strengthClass: strengthClass
    });
  },

  // 验证表单
  validateForm: function () {
    const {
      oldPassword,
      newPassword,
      newPasswordConfirm,
      passwordStrength,
      passwordMatchError,
      passwordValidationError
    } = this.data;

    let canSubmit = true;
    let errorMessage = '';

    // 检查必填字段
    if (!oldPassword) {
      canSubmit = false;
      errorMessage = '请输入旧密码';
    } else if (!newPassword) {
      canSubmit = false;
      errorMessage = '请输入新密码';
    } else if (newPassword.length < 6) {
      canSubmit = false;
      errorMessage = '新密码至少需要6个字符';
    } else if (!newPasswordConfirm) {
      canSubmit = false;
      errorMessage = '请确认新密码';
    } else if (passwordMatchError) {
      canSubmit = false;
      errorMessage = '两次输入的新密码不一致';
    } else if (passwordValidationError) {
      canSubmit = false;
      errorMessage = passwordValidationError;
    } else if (oldPassword === newPassword) {
      canSubmit = false;
      errorMessage = '新密码不能与旧密码相同';
    } else if (passwordStrength.level < 1) {
      canSubmit = false;
      errorMessage = '密码强度太弱，请增强密码';
    }

    this.setData({
      canSubmit: canSubmit,
      errorMessage: errorMessage
    });

    return canSubmit;
  },

  // 提交修改密码
  submitChangePassword: function () {
    if (!this.validateForm()) {
      wx.showToast({
        title: this.data.errorMessage || '请完善表单信息',
        icon: 'none'
      });
      return;
    }

    const that = this;
    const token = wx.getStorageSync('token');

    if (!token) {
      this.handleTokenExpired();
      return;
    }

    const requestData = {
      old_password: this.data.oldPassword,
      new_password: this.data.newPassword,
      new_password_confirm: this.data.newPasswordConfirm
    };

    console.log('提交修改密码请求:', requestData);

    wx.showLoading({
      title: '修改中...',
    });

    wx.request({
      url: app.globalData.baseURL + '/user/change_password/',
      method: 'POST',
      data: requestData,
      header: {
        'Authorization': 'Token ' + token,
        'content-type': 'application/json'
      },
      success: function (res) {
        wx.hideLoading();
        console.log('修改密码响应状态:', res.statusCode);
        console.log('修改密码响应数据:', res.data);

        if (res.statusCode === 200) {
          // 修改成功，清除登录状态，要求重新登录
          that.showSuccessAndLogout('密码修改成功，请重新登录');
        } else if (res.statusCode === 400) {
          // 验证错误
          let errorMsg = '修改失败';
          if (res.data.old_password) {
            errorMsg = res.data.old_password[0];
          } else if (res.data.new_password) {
            errorMsg = res.data.new_password[0];
          } else if (res.data.new_password_confirm) {
            errorMsg = res.data.new_password_confirm[0];
          } else if (res.data.detail) {
            errorMsg = res.data.detail;
          }
          wx.showToast({
            title: errorMsg,
            icon: 'none'
          });
        } else if (res.statusCode === 401) {
          that.handleTokenExpired();
        } else {
          wx.showToast({
            title: '修改失败，请稍后重试',
            icon: 'none'
          });
        }
      },
      fail: function (error) {
        wx.hideLoading();
        console.log('修改密码网络错误:', error);
        wx.showToast({
          title: '网络错误，请检查网络连接',
          icon: 'none'
        });
      }
    });
  },

  // 显示成功提示并退出登录
  showSuccessAndLogout: function (message) {
    const that = this;

    wx.showModal({
      title: '修改成功',
      content: message,
      showCancel: false,
      confirmText: '重新登录',
      success: function (res) {
        if (res.confirm) {
          // 清除所有存储数据
          wx.removeStorageSync('token');
          wx.removeStorageSync('user');
          wx.removeStorageSync('userInfo');

          // 清除全局数据
          if (app.globalData) {
            app.globalData.userInfo = null;
            app.globalData.token = null;
            app.globalData.hasLogin = false;
          }

          console.log('密码修改成功，已清除登录状态');

          // 跳转到登录页面
          wx.reLaunch({
            url: '/pages/login/login?from=password_change'
          });
        }
      }
    });
  },

  // 处理token过期
  handleTokenExpired: function () {
    wx.showModal({
      title: '登录已过期',
      content: '您的登录状态已过期，请重新登录',
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
          wx.reLaunch({
            url: '/pages/login/login'
          });
        }
      }
    });
  },

  // 显示密码要求
  showPasswordRequirements: function () {
    wx.showModal({
      title: '密码要求',
      content: '• 至少6个字符\n• 不能包含连续重复字符（如1111）\n• 不能是连续数值（如1234）\n• 包含大写字母\n• 包含小写字母\n• 包含数字\n• 包含特殊字符',
      showCancel: false,
      confirmText: '知道了'
    });
  }
});