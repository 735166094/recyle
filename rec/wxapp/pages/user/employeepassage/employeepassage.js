// pages/user/employeepassage/employeepassage.js
const app = getApp()

Page({
  data: {
    // 员工认证状态
    isVerified: false,
    employeeName: '',
    department: '',

    // 登录表单
    staff_id: '',
    password: '',
    captcha: '',
    captchaText: '',
    isLoading: false,

    // 弹窗
    showAlert: false,
    alertTitle: '',
    alertMessage: '',

    // 开发中弹窗
    showDevelopmentAlert: false,
    developmentAppName: '',
    developmentMessage: '',

    // 应用列表
    quickAccess: [],
    allApps: [],

    // 员工信息
    employeeInfo: null,

    // 重定向URL和来源页面
    redirectUrl: null,
    fromPage: null
  },

  onLoad: function (options) {
    console.log('员工通道页面加载，参数:', options);

    // 检查参数
    if (options.redirect) {
      const redirectUrl = decodeURIComponent(options.redirect)
      console.log('重定向URL:', redirectUrl)
      this.setData({
        redirectUrl: redirectUrl
      })
    }

    if (options.from) {
      console.log('来源页面:', options.from)
      this.setData({
        fromPage: options.from
      })
    }

    // 检查本地存储中是否有员工认证信息
    this.checkEmployeeStatus();
    // 生成初始验证码
    this.generateCaptcha();
  },

  onPullDownRefresh: function () {
    console.log('下拉刷新触发');

    if (this.data.isVerified) {
      // 如果已经登录，刷新员工信息和应用列表
      this.fetchEmployeeApps();

      // 同时刷新员工信息
      const token = wx.getStorageSync('employeeToken');
      if (token) {
        wx.request({
          url: getApp().globalData.settings.employeeProfile,
          method: 'GET',
          header: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          success: (res) => {
            if (res.data.code === 200) {
              const responseData = res.data.data;

              // 处理不同数据结构 - 添加空值检查
              let userData = null;
              let employeeInfo = null;

              // 检查 responseData 是否存在
              if (!responseData) {
                console.error('刷新员工信息失败: responseData为空');
                wx.showToast({
                  title: '刷新失败，数据为空',
                  icon: 'none',
                  duration: 1000
                });
                return;
              }

              // 新数据结构：responseData.user 和 responseData.employee_detail
              if (responseData.user) {
                userData = responseData.user;
                employeeInfo = responseData.employee_detail;
              } else {
                // 老数据结构：直接是userData
                userData = responseData;
              }

              // 确保 userData 存在
              if (!userData) {
                console.error('刷新员工信息失败: userData为空');
                wx.showToast({
                  title: '刷新失败，用户数据为空',
                  icon: 'none',
                  duration: 1000
                });
                return;
              }

              // 合并数据
              const storageData = {
                ...userData,
                employee_info: employeeInfo || userData.employee_info || null
              };

              wx.setStorageSync('employeeInfo', storageData);

              // 设置页面数据，处理可能不存在的情况
              // 使用可选链和空值合并操作符增强健壮性
              const name = employeeInfo ?
                (employeeInfo.real_name || employeeInfo.username || userData?.username || '员工用户') :
                (userData.real_name || userData.username || userData.nickname || '员工用户');

              const department = employeeInfo ?
                (employeeInfo.department || '企业员工') :
                (userData.department || '企业员工');

              this.setData({
                employeeName: name,
                department: department,
                employeeInfo: storageData
              });

              wx.showToast({
                title: '刷新成功',
                icon: 'success',
                duration: 1000
              });
            } else {
              console.error('刷新员工信息失败:', res.data);
              wx.showToast({
                title: '刷新失败',
                icon: 'none',
                duration: 1000
              });
            }
          },
          fail: (err) => {
            console.error('刷新员工信息请求失败:', err);
            wx.showToast({
              title: '网络错误',
              icon: 'none',
              duration: 1000
            });
          },
          complete: () => {
            // 停止下拉刷新
            wx.stopPullDownRefresh();
          }
        });
      } else {
        wx.stopPullDownRefresh();
      }
    } else {
      // 如果没有登录，只刷新验证码
      this.generateCaptcha();
      wx.stopPullDownRefresh();
    }
  },

  onShow: function () {
    // 页面显示时再次检查状态
    this.checkEmployeeStatus();
  },

  // 检查员工状态
  checkEmployeeStatus: function () {
    console.log('[EmployeePassage] 检查员工状态')

    // 1. 首先检查专门的员工token和信息
    const employeeToken = wx.getStorageSync('employeeToken')
    const employeeInfo = wx.getStorageSync('employeeInfo')

    // 2. 检查普通用户token和信息
    const userToken = wx.getStorageSync('token')
    const userInfo = wx.getStorageSync('userInfo')

    // 3. 首先尝试使用专门的员工登录信息
    if (employeeToken && employeeInfo) {
      console.log('[EmployeePassage] 找到专门的员工登录信息')
      this.setEmployeeData(employeeInfo, employeeToken)
      return
    }

    // 4. 如果没有专门的员工信息，检查普通用户是否为员工
    if (userToken && userInfo) {
      const isEmployee = userInfo.is_staff_member ||
        userInfo.user_type === 'employee' ||
        userInfo.user_type === 'admin'
      const hasStaffId = userInfo.staff_id && userInfo.staff_id.trim() !== ''

      if (isEmployee && hasStaffId) {
        console.log('[EmployeePassage] 普通用户是员工账号，使用其信息')

        // 构建员工信息
        const employeeInfoFromUser = {
          ...userInfo,
          // 确保必要的员工字段存在
          real_name: userInfo.real_name || userInfo.nickname || userInfo.username,
          staff_id: userInfo.staff_id,
          department: userInfo.department || '未分配部门',
          position: userInfo.position || '未分配职位',
          user_type: userInfo.user_type || 'employee'
        }

        // 保存为员工信息，以便后续使用
        wx.setStorageSync('employeeInfo', employeeInfoFromUser)
        wx.setStorageSync('employeeToken', userToken)

        this.setEmployeeData(employeeInfoFromUser, userToken)
        return
      }
    }

    // 5. 都不是员工，显示登录表单
    console.log('[EmployeePassage] 未找到员工信息，显示登录表单')
    this.setData({
      isVerified: false,
      employeeName: '',
      department: '',
      employeeInfo: null
    })

    // 生成验证码
    this.generateCaptcha()
  },

  /**
   * 设置员工数据到页面
   */
  setEmployeeData: function (employeeInfo, token) {
    console.log('[EmployeePassage] 设置员工数据:', employeeInfo)

    let employeeName = '员工用户'
    let department = '企业员工'

    // 处理不同的数据结构
    if (employeeInfo.employee_info) {
      // 新数据结构：employeeInfo.employee_info
      employeeName = employeeInfo.employee_info.real_name ||
        employeeInfo.employee_info.nickname || // 添加昵称
        employeeInfo.real_name ||
        employeeInfo.nickname || // 添加昵称
        employeeInfo.phone || // 添加手机号
        employeeInfo.username ||
        '员工用户'
      department = employeeInfo.employee_info.department ||
        employeeInfo.department ||
        '企业员工'
    } else {
      // 直接访问字段 - 增强字段访问逻辑
      employeeName = employeeInfo.real_name ||
        employeeInfo.nickname ||
        employeeInfo.phone || // 添加手机号
        employeeInfo.username ||
        '员工用户'
      department = employeeInfo.department || '企业员工'
    }

    this.setData({
      isVerified: true,
      employeeName: employeeName,
      department: department,
      employeeInfo: employeeInfo
    })

    // 获取应用列表
    this.fetchEmployeeApps()
  },

  // 生成验证码
  generateCaptcha: function () {
    const chars = 'ABCDEFGHJKMNPQRSTWXYZ23456789';
    let captcha = '';
    for (let i = 0; i < 4; i++) {
      captcha += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    this.setData({
      captchaText: captcha
    });
  },

  // 刷新验证码
  refreshCaptcha: function () {
    this.generateCaptcha();
    this.setData({
      captcha: ''
    });
  },

  // 员工工号输入
  onStaffIdInput: function (e) {
    this.setData({
      staff_id: e.detail.value
    });
  },

  // 密码输入
  onPasswordInput: function (e) {
    this.setData({
      password: e.detail.value
    });
  },

  // 验证码输入
  onCaptchaInput: function (e) {
    console.log('验证码输入:', e.detail.value);
    this.setData({
      captcha: e.detail.value
    });
  },

  // 验证码确认
  onCaptchaConfirm: function () {
    console.log('验证码输入完成，开始登录');
    this.verifyEmployee();
  },

  // 验证员工身份 
  verifyEmployee: function () {
    const that = this;
    const {
      staff_id,
      password,
      captcha,
      captchaText
    } = this.data;

    console.log('验证员工身份，参数:', {
      staff_id,
      password,
      captcha,
      captchaText
    });

    // 验证输入
    if (!staff_id || staff_id.trim() === '') {
      this.showAlert('提示', '请输入员工工号');
      return;
    }

    if (!password || password.trim() === '') {
      this.showAlert('提示', '请输入员工密码');
      return;
    }

    if (!captcha || captcha.trim() === '') {
      this.showAlert('提示', '请输入验证码');
      return;
    }

    // 开发环境下可以跳过验证码验证
    const isDev = true; // 可以根据环境配置调整
    if (!isDev && captcha.toUpperCase() !== captchaText.toUpperCase()) {
      this.showAlert('验证失败', '验证码错误，请重新输入');
      this.generateCaptcha();
      this.setData({
        captcha: ''
      });
      return;
    }

    that.setData({
      isLoading: true
    });

    // 调用员工登录API - 在函数内部获取app实例
    const appInstance = getApp();

    wx.request({
      url: appInstance.globalData.settings.employeeLogin,
      method: 'POST',
      data: {
        staff_id: staff_id.trim(),
        password: password.trim(),
        captcha: isDev ? '' : captcha.trim() // 开发环境不传验证码
      },
      header: {
        'Content-Type': 'application/json'
      },
      success: function (res) {
        console.log('登录API响应:', res);
        that.setData({
          isLoading: false
        });

        if (res.data.code === 200) {
          // 登录成功
          const userData = res.data.data.user;
          const tokenData = res.data.data.token;
          const apps = res.data.data.apps || [];

          console.log('登录成功，用户数据:', userData);
          console.log('应用数据:', apps);

          // 保存员工token和用户信息（员工通道专用）
          wx.setStorageSync('employeeToken', tokenData.access);
          wx.setStorageSync('employeeRefreshToken', tokenData.refresh);
          wx.setStorageSync('employeeInfo', userData);

          // 同步员工登录状态到全局登录状态
          that.syncEmployeeToGlobalLogin(userData, tokenData.access);

          // 处理应用数据
          const quickAccess = apps.slice(0, 4); // 前4个作为快速访问
          const allApps = apps;

          that.setData({
            isVerified: true,
            employeeName: userData.employee_info?.real_name || userData.real_name || userData.username || '员工用户',
            department: userData.employee_info?.department || userData.department || '企业员工',
            employeeInfo: userData,
            quickAccess: quickAccess,
            allApps: allApps,
            staff_id: '', // 清空输入框
            password: '', // 清空输入框
            captcha: '' // 清空输入框
          });

          wx.showToast({
            title: '登录成功',
            icon: 'success',
            duration: 1500
          });

          // 登录成功后的跳转逻辑
          setTimeout(() => {
            that.redirectAfterEmployeeLogin();
          }, 1500);

        } else {
          // 登录失败
          console.log('登录失败，响应:', res.data);
          that.showAlert('登录失败', res.data.message || '登录失败，请重试');
          that.generateCaptcha();
          that.setData({
            captcha: '',
            password: '' // 清空密码
          });
        }
      },
      fail: function (err) {
        console.error('登录请求失败:', err);
        that.setData({
          isLoading: false
        });
        that.showAlert('网络错误', '网络请求失败，请检查网络连接');
        that.generateCaptcha();
        that.setData({
          captcha: ''
        });
      }
    });
  },

  /**
   * 同步员工登录状态到全局登录状态
   * 员工登录后，整个小程序都可以识别为已登录状态
   */
  syncEmployeeToGlobalLogin: function (employeeData, token) {
    console.log('开始同步员工登录状态到全局状态');

    // 构建统一的用户信息格式
    const unifiedUserInfo = {
      id: employeeData.id || employeeData.employee_id,
      username: employeeData.username || employeeData.staff_id,
      email: employeeData.email || '',
      phone: employeeData.phone || '',
      nickname: employeeData.nickname || employeeData.real_name || employeeData.username,
      avatar_url: employeeData.avatar_url || employeeData.avatar || '',
      avatar: employeeData.avatar || employeeData.avatar_url || '',
      gender: employeeData.gender || 0,
      country: employeeData.country || '',
      province: employeeData.province || '',
      city: employeeData.city || '',
      points: employeeData.points || 0,
      is_staff: true, // 关键：设置为true，表示是员工
      is_staff_member: true, // 员工标识
      is_verified: true, // 员工默认已验证
      real_name: employeeData.real_name || employeeData.nickname || employeeData.username,
      staff_id: employeeData.staff_id,
      employee_id: employeeData.employee_id || employeeData.id,
      department: employeeData.department || '未分配部门',
      position: employeeData.position || '未分配职位',
      user_type: employeeData.user_type || 'employee',
      is_active: true,
      is_phone_bound: employeeData.is_phone_bound || false,
      is_wechat_bound: employeeData.is_wechat_bound || false,
      created_at: employeeData.created_at || '',
      updated_at: employeeData.updated_at || '',
      last_login: employeeData.last_login || '',
      last_login_time: employeeData.last_login_time || '',
      permissions: employeeData.permissions || [],
      groups: employeeData.groups || [],
      // 包含token信息
      token: employeeData.token || {
        access: token,
        refresh: wx.getStorageSync('employeeRefreshToken') || ''
      }
    };

    // 保存到全局存储（小程序全局状态）
    const app = getApp();
    if (app && app.globalData) {
      app.globalData.userInfo = unifiedUserInfo;
      app.globalData.isLoggedIn = true;
      app.globalData.isGuest = false;
      app.globalData.token = token;
      app.globalData.userType = 'employee';

      console.log('已更新全局用户状态', {
        userInfo: unifiedUserInfo.username,
        isLoggedIn: app.globalData.isLoggedIn,
        userType: app.globalData.userType
      });
    }

    // 保存到本地存储（兼容普通用户登录的字段）
    wx.setStorageSync('userInfo', unifiedUserInfo);
    wx.setStorageSync('token', token);
    wx.setStorageSync('refresh_token', wx.getStorageSync('employeeRefreshToken') || '');
    wx.setStorageSync('isLogin', true);
    wx.setStorageSync('isGuest', false);
    wx.setStorageSync('userType', 'employee');
    wx.setStorageSync('loginTime', new Date().getTime());

    console.log('员工登录状态已同步到全局登录状态');
  },

  /**
   * 员工登录后的跳转逻辑
   * 根据来源页面决定跳转行为
   */
  redirectAfterEmployeeLogin: function () {
    const that = this;
    const fromPage = this.data.fromPage;
    const redirectUrl = this.data.redirectUrl;

    console.log('员工登录后跳转逻辑:', {
      fromPage,
      redirectUrl
    });

    // 情况1：从login页面跳转过来的，返回上一页
    if (fromPage === 'login') {
      console.log('从登录页面跳转过来，返回上一页');
      wx.navigateBack({
        delta: 1,
        success: () => {
          console.log('返回登录页面成功');
        },
        fail: (err) => {
          console.error('返回登录页面失败:', err);
          // 返回失败，跳转到用户中心
          that.redirectToDefaultPage();
        }
      });
      return;
    }

    // 情况2：有重定向URL
    if (redirectUrl) {
      console.log('有重定向URL，跳转到:', redirectUrl);

      // 检查是否是tab页
      const tabPages = [
        '/pages/index/index',
        '/pages/mall/index/index',
        '/pages/news/index/index',
        '/pages/user/index/index'
      ];

      if (tabPages.includes(redirectUrl)) {
        // 如果是tab页，使用switchTab
        wx.switchTab({
          url: redirectUrl,
          success: () => {
            console.log('跳转到tab页成功');
          },
          fail: (err) => {
            console.error('跳转到tab页失败:', err);
            // 失败后跳转到员工通道页面
            that.redirectToEmployeePage();
          }
        });
      } else {
        // 如果是普通页面，使用redirectTo
        wx.redirectTo({
          url: redirectUrl,
          success: () => {
            console.log('跳转到重定向页面成功');
          },
          fail: (err) => {
            console.error('跳转到重定向页面失败:', err);
            // 失败后跳转到员工通道页面
            that.redirectToEmployeePage();
          }
        });
      }
      return;
    }

    // 情况3：默认跳转到员工通道页面
    that.redirectToEmployeePage();
  },

  /**
   * 跳转到员工通道页面（留在当前页面）
   */
  redirectToEmployeePage: function () {
    console.log('停留在员工通道页面');
    // 已经是员工通道页面，不需要跳转
    this.fetchEmployeeApps();
  },

  /**
   * 跳转到默认页面（用户中心）
   */
  redirectToDefaultPage: function () {
    console.log('跳转到默认页面（用户中心）');
    wx.switchTab({
      url: '/pages/user/index/index',
      success: () => {
        console.log('跳转到个人中心成功');
      },
      fail: (err) => {
        console.error('跳转到个人中心失败:', err);
        // 失败后重试
        wx.redirectTo({
          url: '/pages/user/index/index'
        });
      }
    });
  },

  // 内部页面跳转
  navigateToInternalPage: function (appData, accessInfo) {
    console.log('内部页面跳转:', {
      appId: appData.app_id,
      appName: appData.app_name,
      openType: appData.open_type,
      accessInfo: accessInfo
    });

    const path = accessInfo.path || '';
    const appName = appData.app_name || '应用';

    // 检查是否开发中
    if (appData.app_config?.status === 'developing') {
      console.log('应用正在开发中:', appName);
      this.showAlert('系统提示', `${appName}正在开发中，敬请期待！`);
      return;
    }

    // 如果没有配置路径
    if (!path) {
      console.log('应用路径未配置:', appName);
      this.showAlert('系统提示', `${appName}功能正在开发中，请稍后使用！`);
      return;
    }

    // 获取员工登录信息
    const employeeToken = wx.getStorageSync('employeeToken');
    const employeeInfo = wx.getStorageSync('employeeInfo');

    console.log('当前登录状态:', {
      hasEmployeeToken: !!employeeToken,
      hasEmployeeInfo: !!employeeInfo
    });

    // 构建跳转URL
    let targetPath = path;

    // 只有OCR系统需要特殊处理认证信息
    if (targetPath.includes('/pages/ocr/') || targetPath.includes('/pages/vin/')) {
      console.log('跳转到OCR/VIN页面，添加认证参数');

      const separator = targetPath.includes('?') ? '&' : '?';

      // 传递token
      if (employeeToken) {
        targetPath = `${targetPath}${separator}access_token=${encodeURIComponent(employeeToken)}`;
      }

      // 传递用户信息
      if (employeeInfo) {
        const userInfoStr = encodeURIComponent(JSON.stringify(employeeInfo));
        targetPath = `${targetPath}&user_info=${userInfoStr}`;
      }

      // 传递用户类型
      targetPath = `${targetPath}&user_type=employee`;
    }

    console.log('最终跳转URL:', targetPath);

    // 检查页面是否存在
    wx.navigateTo({
      url: targetPath,
      success: function () {
        console.log('页面跳转成功');
      },
      fail: function (err) {
        console.error('页面跳转失败:', err);

        // 处理跳转失败
        if (err.errMsg && err.errMsg.includes('fail page')) {
          wx.showToast({
            title: '页面正在开发中',
            icon: 'none',
            duration: 2000
          });
        } else {
          wx.showToast({
            title: '跳转失败',
            icon: 'none'
          });
        }
      }
    });
  },

  // 打开WebView 
  openWebView: function (appData, accessInfo) {
    console.log('打开WebView:', accessInfo);

    const url = accessInfo.url || '';
    const appName = appData.app_name || '应用';

    if (!url) {
      console.log('WebView地址未配置:', appName);
      this.showAlert('系统提示', `${appName}功能正在开发中，请稍后使用！`);
      return;
    }

    // 检查是否开发中
    if (appData.app_config?.status === 'developing') {
      console.log('应用正在开发中:', appName);
      this.showAlert('系统提示', `${appName}正在开发中，敬请期待！`);
      return;
    }

    // 构建WebView参数
    let webviewUrl = url;

    // 如果需要传递认证信息
    if (appData.access_token) {
      const separator = url.includes('?') ? '&' : '?';
      webviewUrl = `${url}${separator}access_token=${appData.access_token}`;
    }

    // 跳转到WebView页面
    wx.navigateTo({
      url: `/pages/webview/webview?url=${encodeURIComponent(webviewUrl)}`,
      success: function () {
        console.log('WebView跳转成功');
      },
      fail: function (err) {
        console.error('WebView跳转失败:', err);
        wx.showToast({
          title: '跳转失败',
          icon: 'none'
        });
      }
    });
  },

  // 跳转其他小程序  
  navigateToMiniProgram: function (appData, accessInfo) {
    console.log('跳转小程序:', accessInfo);

    const path = accessInfo.path || '';
    const appName = appData.app_name || '应用';

    if (!path) {
      console.log('小程序路径未配置:', appName);
      this.showAlert('系统提示', `${appName}功能正在开发中，请稍后使用！`);
      return;
    }

    // 检查是否开发中
    if (appData.app_config?.status === 'developing') {
      console.log('应用正在开发中:', appName);
      this.showAlert('系统提示', `${appName}正在开发中，敬请期待！`);
      return;
    }

    // 获取小程序appId（从配置中或固定值）
    const appId = appData.app_config?.app_id || appData.app_id || '';

    if (!appId) {
      this.showAlert('系统提示', '小程序配置信息不完整，请联系管理员');
      return;
    }

    wx.navigateToMiniProgram({
      appId: appId,
      path: path,
      success: function (res) {
        console.log('跳转小程序成功:', res);
      },
      fail: function (err) {
        console.error('跳转小程序失败:', err);

        if (err.errMsg.includes('app not found')) {
          wx.showToast({
            title: '未找到对应小程序',
            icon: 'none'
          });
        } else {
          wx.showToast({
            title: '跳转失败',
            icon: 'none'
          });
        }
      }
    });
  },

  // 退出登录 
  logout: function () {
    const that = this;

    // 在函数内部获取app实例，确保总是最新的
    const appInstance = getApp();

    wx.showModal({
      title: '确认退出',
      content: '确定要退出员工账号吗？',
      confirmColor: '#e74c3c',
      success: (res) => {
        if (res.confirm) {
          // 调用退出接口
          const token = wx.getStorageSync('employeeToken');

          if (token) {
            // 使用函数内部获取的appInstance
            wx.request({
              url: appInstance.globalData.settings.employeeLogout,
              method: 'POST',
              header: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
              },
              success: function () {
                console.log('退出登录成功');
              },
              fail: function (err) {
                console.error('退出登录失败:', err);
              }
            });
          }

          // 清除员工信息
          wx.removeStorageSync('employeeToken');
          wx.removeStorageSync('employeeRefreshToken');
          wx.removeStorageSync('employeeInfo');

          // 清除员工相关的全局登录信息
          wx.removeStorageSync('token');
          wx.removeStorageSync('refresh_token');
          wx.removeStorageSync('userInfo');
          wx.removeStorageSync('isLogin');
          wx.removeStorageSync('isGuest');
          wx.removeStorageSync('userType');
          wx.removeStorageSync('loginTime');

          // 清除全局状态中的员工信息
          if (appInstance && appInstance.globalData) {
            appInstance.globalData.employeeInfo = null;
            appInstance.globalData.isEmployeeLoggedIn = false;
            appInstance.globalData.employeeToken = null;

            // 注意：不清除普通用户信息，这样普通用户登录状态仍然保持
          }

          // 重置页面状态
          that.setData({
            isVerified: false,
            staff_id: '',
            password: '',
            captcha: '',
            employeeName: '',
            department: '',
            employeeInfo: null,
            quickAccess: [],
            allApps: []
          });

          // 生成新的验证码
          that.generateCaptcha();

          wx.showToast({
            title: '已退出员工通道',
            icon: 'success',
            duration: 1500
          });
        }
      }
    });
  },

  // 获取员工应用列表
  fetchEmployeeApps: function () {
    const that = this;
    const token = wx.getStorageSync('employeeToken');

    if (!token) {
      console.log('没有找到token，无法获取应用列表');
      return;
    }

    console.log('获取应用列表，token:', token.substring(0, 20) + '...');

    wx.request({
      url: app.globalData.settings.employeeApps,
      method: 'GET',
      header: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      success: function (res) {
        console.log('获取应用列表响应:', res);
        if (res.data.code === 200) {
          const apps = res.data.data || [];
          const quickAccess = apps.slice(0, 4);

          console.log('应用列表:', apps);

          that.setData({
            quickAccess: quickAccess,
            allApps: apps
          });
        } else if (res.data.code === 401) {
          console.log('token过期，尝试刷新');
          // token过期，尝试刷新
          that.refreshEmployeeToken();
        } else {
          console.log('获取应用列表失败:', res.data);
        }
      },
      fail: function (err) {
        console.error('获取应用列表失败:', err);
      }
    });
  },

  // 刷新token
  refreshEmployeeToken: function () {
    const that = this;
    const refreshToken = wx.getStorageSync('employeeRefreshToken');

    if (!refreshToken) {
      console.log('没有refresh token，退出登录');
      that.logout();
      return;
    }

    console.log('刷新token，refreshToken:', refreshToken.substring(0, 20) + '...');

    wx.request({
      url: app.globalData.settings.tokenRefresh,
      method: 'POST',
      data: {
        refresh: refreshToken
      },
      header: {
        'Content-Type': 'application/json'
      },
      success: function (res) {
        console.log('刷新token响应:', res);
        if (res.data.code === 200 && res.data.data.access) {
          const newAccessToken = res.data.data.access;
          wx.setStorageSync('employeeToken', newAccessToken);
          console.log('token刷新成功，新token:', newAccessToken.substring(0, 20) + '...');
          // 重新获取应用列表
          that.fetchEmployeeApps();
        } else {
          console.log('token刷新失败:', res.data);
          that.logout();
        }
      },
      fail: function (err) {
        console.error('刷新token失败:', err);
        that.logout();
      }
    });
  },

  // 访问应用
  navigateToSystem: function (e) {
    const that = this;
    const appId = e.currentTarget.dataset.appid;
    const token = wx.getStorageSync('employeeToken');

    if (!token) {
      this.showAlert('提示', '请先登录');
      return;
    }

    console.log('访问应用:', appId);

    wx.showLoading({
      title: '加载中...',
    });

    // 获取应用访问权限
    wx.request({
      url: getApp().globalData.settings.employeeAccessApp,
      method: 'POST',
      data: {
        app_id: appId
      },
      header: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      success: function (res) {
        wx.hideLoading();
        console.log('访问应用响应:', res);

        if (res.data.code === 200) {
          const appData = res.data.data;
          const openType = appData.open_type || 'internal';
          const accessInfo = appData.access_info || {};

          // 保存应用访问令牌
          if (appData.access_token) {
            appData.access_token = appData.access_token;
          }

          console.log('应用类型:', openType, '访问信息:', accessInfo);

          // 根据打开方式执行不同的跳转逻辑
          switch (openType) {
            case 'internal':
              // 内部页面跳转
              that.navigateToInternalPage(appData, accessInfo);
              break;
            case 'webview':
              // WebView打开外部网页
              that.openWebView(appData, accessInfo);
              break;
            case 'miniapp':
              // 跳转其他小程序
              that.navigateToMiniProgram(appData, accessInfo);
              break;
            default:
              // 默认内部跳转
              that.navigateToInternalPage(appData, accessInfo);
              break;
          }
        } else {
          console.log('访问应用失败:', res.data);
          that.showAlert('访问失败', res.data.message || '应用访问失败');
        }
      },
      fail: function (err) {
        wx.hideLoading();
        console.error('访问应用失败:', err);

        // 网络错误处理
        if (err.errMsg && err.errMsg.includes('timeout')) {
          that.showAlert('网络超时', '请求超时，请检查网络连接');
        } else {
          that.showAlert('网络错误', '应用访问失败，请检查网络连接');
        }
      }
    });
  },

  // 显示弹窗
  showAlert: function (title, message) {
    console.log('显示弹窗:', title, message);
    this.setData({
      showAlert: true,
      alertTitle: title,
      alertMessage: message
    });
  },

  // 显示开发中弹窗
  showDevelopmentAlert: function (appName, message) {
    console.log('显示开发中弹窗:', appName, message);
    this.setData({
      showDevelopmentAlert: true,
      developmentAppName: appName || '应用',
      developmentMessage: message || '系统正在开发中，敬请期待！'
    });
  },

  // 隐藏弹窗
  hideAlert: function () {
    this.setData({
      showAlert: false
    });
  },

  // 隐藏开发中弹窗
  hideDevelopmentAlert: function () {
    this.setData({
      showDevelopmentAlert: false
    });
  },

  // 拨打电话
  makeCall: function (e) {
    const phone = e.currentTarget.dataset.phone;
    wx.makePhoneCall({
      phoneNumber: phone,
      success: () => {
        console.log('拨打电话成功');
      },
      fail: (err) => {
        console.error('拨打电话失败', err);
        wx.showToast({
          title: '拨号失败',
          icon: 'none'
        });
      }
    });
  },

  onShareAppMessage: function () {
    return {
      title: '企业员工通道',
      path: '/pages/user/employeepassage/employeepassage'
    };
  }
});