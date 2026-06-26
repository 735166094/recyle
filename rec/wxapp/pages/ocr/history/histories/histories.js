import api from '../../../../config/settings.js'

Page({
  data: {
    historyRecords: [],
    isLoading: false,
    isLoggedIn: false,

    // 证件类型筛选
    certificateTypes: [],
    certificateTypeNames: ['全部类型'],
    selectedCertificateTypeIndex: 0,
    selectedCertificateTypeName: '',

    // 时间筛选
    dateRange: ['全部时间', '今天', '最近7天', '最近30天', '自定义'],
    selectedDateIndex: 0,
    startDate: '',
    endDate: '',

    // 自定义日期
    showCustomDatePicker: false,
    customStartDate: '',
    customEndDate: '',

    // 分页
    page: 1,
    pageSize: 20,
    hasMore: true,
    totalCount: 0,

    // 其他
    errorMessage: '',
    lastUpdateTime: '',
    hasActiveFilters: false
  },

  onLoad: function (options) {
    console.log('histories页面加载，options:', options);
    this.verifyUserConsistency();

    // 检查是否有传递的token参数（从员工通道跳转时可能会传递）
    if (options.access_token) {
      console.log('接收到传递的access_token');
      wx.setStorageSync('token', options.access_token);
    }

    if (options.user_info) {
      try {
        const userInfo = JSON.parse(decodeURIComponent(options.user_info));
        console.log('接收到传递的用户信息:', userInfo);
        wx.setStorageSync('user', userInfo);
      } catch (e) {
        console.error('解析用户信息失败:', e);
      }
    }

    this.checkLoginStatus();
    this.initDateFilter();
    if (this.data.isLoggedIn) {
      this.fetchCertificateTypes();
    }
  },

  onShow: function () {
    console.log('histories页面显示');
    this.checkLoginStatus();
    if (this.data.isLoggedIn) {
      this.loadHistoryRecords(true);
    }
  },
  onReachBottom: function () {
    if (this.data.hasMore && !this.data.isLoading) {
      this.loadMoreRecords();
    }
  },

  onPullDownRefresh: function () {
    this.loadHistoryRecords(true);
    wx.stopPullDownRefresh();
  },

  // 检查登录状态
  checkLoginStatus: function () {
    // 优先检查员工登录状态
    const employeeToken = wx.getStorageSync('employeeToken');
    const employeeInfo = wx.getStorageSync('employeeInfo');

    // 再检查普通OCR系统登录状态
    const token = wx.getStorageSync('token');
    const user = wx.getStorageSync('user');

    console.log('检查登录状态:', {
      employeeToken: !!employeeToken,
      employeeInfo: !!employeeInfo,
      token: !!token,
      user: !!user
    });

    // 如果员工已登录，使用员工登录信息
    if (employeeToken && employeeInfo) {
      console.log('使用员工登录信息');

      // 确保token同步到OCR系统（兼容性处理）
      if (!token) {
        wx.setStorageSync('token', employeeToken);
        console.log('同步员工token到OCR系统');
      }
      if (!user) {
        wx.setStorageSync('user', employeeInfo);
        console.log('同步员工信息到OCR系统');
      }

      this.setData({
        isLoggedIn: true
      });
      return true;
    }

    // 如果普通OCR系统已登录
    if (token && user) {
      console.log('使用OCR系统登录信息');
      this.setData({
        isLoggedIn: true
      });
      return true;
    }

    // 未登录
    this.setData({
      isLoggedIn: false,
      historyRecords: []
    });
    this.redirectToLogin();
    return false;
  },

  // 跳转到登录页
  redirectToLogin: function () {
    wx.redirectTo({
      url: '/pages/login/login?redirect=' + encodeURIComponent('/pages/ocr/history/histories/histories')
    });
  },

  // 初始化日期筛选
  initDateFilter: function () {
    const today = new Date();
    const todayStr = today.toISOString().split('T')[0];

    this.setData({
      startDate: todayStr,
      endDate: todayStr,
      customStartDate: todayStr,
      customEndDate: todayStr
    });
  },

  // 获取证件类型列表
  fetchCertificateTypes: function () {
    const that = this;

    // 获取所有可能的Token
    const employeeToken = wx.getStorageSync('employeeToken');
    const token = wx.getStorageSync('token');

    console.log('Token检查:', {
      employeeToken: !!employeeToken,
      token: !!token
    });

    // 确定使用哪个Token和Token类型
    let authToken = '';
    let tokenType = '';

    if (employeeToken) {
      authToken = employeeToken;
      tokenType = 'Bearer';
      console.log('使用员工Token:', authToken.substring(0, 20) + '...');
    } else if (token) {
      authToken = token;
      tokenType = 'Token';
      console.log('使用OCR Token:', authToken.substring(0, 20) + '...');
    }

    if (!authToken) {
      console.error('没有可用的Token');
      that.setData({
        errorMessage: '请先登录'
      });
      return;
    }

    // 构建请求头
    const headers = {
      'Authorization': `${tokenType} ${authToken}`
    };

    console.log('请求头:', headers);

    wx.request({
      url: api.recognitionTypes,
      method: 'GET',
      header: headers,
      success: function (res) {
        if (res.statusCode === 200) {
          // ... 处理成功响应 ...
        } else if (res.statusCode === 401) {
          console.log('认证失败，清除本地存储并跳转到登录页');
          // 清除所有可能存在的Token
          wx.removeStorageSync('employeeToken');
          wx.removeStorageSync('token');
          wx.removeStorageSync('user');
          wx.removeStorageSync('employeeInfo');
          that.redirectToLogin();
        }
      }
    });
  },

  // 证件类型选择变化
  bindCertificateTypeChange: function (e) {
    const index = parseInt(e.detail.value);
    const certificateTypeName = index === 0 ? '' : this.data.certificateTypeNames[index];

    console.log('选择的证件类型索引:', index, '名称:', certificateTypeName);

    this.setData({
      selectedCertificateTypeIndex: index,
      selectedCertificateTypeName: certificateTypeName
    });
  },

  // 日期范围选择变化
  bindDateRangeChange: function (e) {
    const index = parseInt(e.detail.value);
    this.setData({
      selectedDateIndex: index,
      showCustomDatePicker: index === 4 // 如果是"自定义"选项，显示自定义日期选择器
    }, () => {
      if (index !== 4) {
        this.updateDateRange();
      }
    });
  },

  // 自定义开始日期变化
  bindCustomStartDateChange: function (e) {
    this.setData({
      customStartDate: e.detail.value
    });
  },

  // 自定义结束日期变化
  bindCustomEndDateChange: function (e) {
    this.setData({
      customEndDate: e.detail.value
    });
  },

  // 更新日期范围
  updateDateRange: function () {
    const today = new Date();
    let startDate = '';
    let endDate = today.toISOString().split('T')[0];

    switch (this.data.selectedDateIndex) {
      case 0: // 全部时间
        startDate = '';
        endDate = '';
        break;
      case 1: // 今天
        startDate = endDate;
        break;
      case 2: // 最近7天
        const sevenDaysAgo = new Date(today);
        sevenDaysAgo.setDate(today.getDate() - 6);
        startDate = sevenDaysAgo.toISOString().split('T')[0];
        break;
      case 3: // 最近30天
        const thirtyDaysAgo = new Date(today);
        thirtyDaysAgo.setDate(today.getDate() - 29);
        startDate = thirtyDaysAgo.toISOString().split('T')[0];
        break;
    }

    this.setData({
      startDate: startDate,
      endDate: endDate
    });
  },

  // 应用筛选
  applyFilters: function () {
    // 如果是自定义日期，使用自定义日期值
    if (this.data.selectedDateIndex === 4) {
      if (!this.data.customStartDate || !this.data.customEndDate) {
        wx.showToast({
          title: '请选择完整的日期范围',
          icon: 'none'
        });
        return;
      }
      this.setData({
        startDate: this.data.customStartDate,
        endDate: this.data.customEndDate
      });
    }

    this.loadHistoryRecords(true);
  },

  // 重置筛选
  resetFilters: function () {
    this.setData({
      selectedCertificateTypeIndex: 0,
      selectedCertificateTypeName: '',
      selectedDateIndex: 0,
      startDate: '',
      endDate: '',
      customStartDate: new Date().toISOString().split('T')[0],
      customEndDate: new Date().toISOString().split('T')[0],
      showCustomDatePicker: false,
      hasActiveFilters: false
    }, () => {
      this.loadHistoryRecords(true);
    });
  },

  // 移除证件类型筛选
  removeCertificateTypeFilter: function () {
    this.setData({
      selectedCertificateTypeIndex: 0,
      selectedCertificateTypeName: ''
    }, () => {
      this.loadHistoryRecords(true);
    });
  },

  // 移除日期筛选
  removeDateFilter: function () {
    this.setData({
      selectedDateIndex: 0,
      startDate: '',
      endDate: ''
    }, () => {
      this.loadHistoryRecords(true);
    });
  },

  // 移除自定义日期筛选
  removeCustomDateFilter: function () {
    this.setData({
      selectedDateIndex: 0,
      startDate: '',
      endDate: '',
      showCustomDatePicker: false
    }, () => {
      this.loadHistoryRecords(true);
    });
  },

  loadHistoryRecords: function (refresh = true) {
    if (!this.data.isLoggedIn) return;

    const that = this;

    console.log('=== 开始加载历史记录 ===');
    console.log('当前存储状态:', {
      employeeToken: wx.getStorageSync('employeeToken') ? wx.getStorageSync('employeeToken').substring(0, 20) + '...' : '无',
      token: wx.getStorageSync('token') ? wx.getStorageSync('token').substring(0, 20) + '...' : '无',
      hasUser: !!wx.getStorageSync('user'),
      hasEmployeeInfo: !!wx.getStorageSync('employeeInfo'),
      isLoggedIn: this.data.isLoggedIn
    });

    // ⚠️ 强制优先使用员工token
    const employeeToken = wx.getStorageSync('employeeToken');
    const token = wx.getStorageSync('token');

    console.log('Token详情:', {
      employeeToken: employeeToken ? `长度: ${employeeToken.length}, 前20位: ${employeeToken.substring(0, 20)}...` : '无',
      token: token ? `长度: ${token.length}, 前20位: ${token.substring(0, 20)}...` : '无',
      tokensMatch: employeeToken === token
    });

    // 确定使用哪个Token和Token类型
    let authToken = '';
    let tokenType = '';

    // 强制优先级：employeeToken > token
    if (employeeToken) {
      authToken = employeeToken;
      tokenType = 'Bearer';
      console.log('✅ 使用员工Token，类型: Bearer');

      // 确保同步到普通token
      if (!token || token !== employeeToken) {
        wx.setStorageSync('token', employeeToken);
        console.log('已将员工Token同步到普通token');
      }
    } else if (token) {
      authToken = token;
      // 判断token类型
      if (authToken.startsWith('ey') && authToken.includes('.') && authToken.split('.').length === 3) {
        tokenType = 'Bearer';
        console.log('✅ 使用普通Token，类型: Bearer (JWT)');
      } else {
        tokenType = 'Token';
        console.log('✅ 使用普通Token，类型: Token');
      }
    }

    if (!authToken) {
      console.error('❌ 没有可用的Token');
      that.setData({
        errorMessage: '请先登录'
      });
      wx.showToast({
        title: '请先登录',
        icon: 'none'
      });
      return;
    }

    // 构建请求头
    const headers = {
      'Authorization': `${tokenType} ${authToken}`,
      'Content-Type': 'application/json'
    };

    console.log('请求头:', headers);

    // 构建请求参数
    const params = {
      page: this.data.page,
      page_size: this.data.pageSize
    };

    // 添加筛选参数
    if (this.data.selectedCertificateTypeName && this.data.selectedCertificateTypeName !== '全部类型') {
      params.certificate_type = this.data.selectedCertificateTypeName;
    }

    if (this.data.startDate && this.data.selectedDateIndex !== 0) {
      params.start_date = this.data.startDate;
    }

    if (this.data.endDate && this.data.selectedDateIndex !== 0) {
      params.end_date = this.data.endDate;
    }

    console.log('请求参数:', params);

    this.setData({
      isLoading: true,
      errorMessage: ''
    });

    wx.request({
      url: api.myRecords,
      method: 'GET',
      header: headers,
      data: params,
      success: function (res) {
        console.log('历史记录响应:', res);

        if (res.statusCode === 200) {
          const responseData = res.data;
          const results = responseData.results || [];
          const totalCount = responseData.count || 0;

          console.log(`获取到 ${results.length} 条记录，总记录数: ${totalCount}`);

          // 🔧 去重处理
          let newRecords = results;

          // 如果是刷新，直接使用新数据
          if (refresh) {
            // 去重：基于id的唯一性
            const uniqueRecords = [];
            const seenIds = new Set();

            newRecords.forEach(record => {
              if (record.id && !seenIds.has(record.id)) {
                seenIds.add(record.id);
                uniqueRecords.push(record);
              } else {
                console.warn(`发现重复记录ID: ${record.id}，已过滤`);
              }
            });

            newRecords = uniqueRecords;

            that.setData({
              historyRecords: newRecords,
              totalCount: responseData.count || 0,
              hasMore: responseData.next ? true : false,
              isLoading: false,
              lastUpdateTime: that.formatTime(new Date(), 'time')
            });

          } else {
            // 如果是加载更多，合并并去重
            const currentRecords = that.data.historyRecords || [];
            const seenIds = new Set(currentRecords.map(r => r.id));
            const uniqueNewRecords = [];

            newRecords.forEach(record => {
              if (record.id && !seenIds.has(record.id)) {
                seenIds.add(record.id);
                uniqueNewRecords.push(record);
              } else {
                console.warn(`发现重复记录ID: ${record.id}，已过滤`);
              }
            });

            const mergedRecords = currentRecords.concat(uniqueNewRecords);

            that.setData({
              historyRecords: mergedRecords,
              hasMore: responseData.next ? true : false,
              isLoading: false,
              lastUpdateTime: that.formatTime(new Date(), 'time')
            });
          }

          console.log(`✅ 成功加载 ${that.data.historyRecords.length} 条记录，已去重`);

        } else {
          console.error('请求失败:', res);
          that.setData({
            isLoading: false,
            errorMessage: '加载失败，请重试'
          });
        }
      },
      fail: function (err) {
        console.error('请求失败:', err);
        that.setData({
          isLoading: false,
          errorMessage: '网络错误，请检查连接'
        });
      }
    });
  },

  verifyUserConsistency: function () {
    console.log('=== 开始验证用户一致性 ===');

    // 获取所有可能的存储信息
    const employeeToken = wx.getStorageSync('employeeToken');
    const token = wx.getStorageSync('token');
    const employeeInfo = wx.getStorageSync('employeeInfo');
    const user = wx.getStorageSync('user');

    console.log('存储信息:', {
      employeeToken: employeeToken ? employeeToken.substring(0, 20) + '...' : '无',
      token: token ? token.substring(0, 20) + '...' : '无',
      hasEmployeeInfo: !!employeeInfo,
      hasUser: !!user
    });

    // 检查token是否一致
    if (employeeToken && token && employeeToken !== token) {
      console.warn('⚠️ Token不一致！员工Token与普通Token不同');

      // 强制使用员工Token
      wx.setStorageSync('token', employeeToken);
      console.log('已强制同步员工Token到普通token');

      // 如果员工信息存在，也同步到普通用户信息
      if (employeeInfo && !user) {
        wx.setStorageSync('user', employeeInfo);
        console.log('已同步员工信息到用户信息');
      }
    }

    // 检查用户信息是否存在
    if (!wx.getStorageSync('user')) {
      if (employeeInfo) {
        wx.setStorageSync('user', employeeInfo);
        console.log('已从员工信息恢复用户信息');
      }
    }

    console.log('=== 用户一致性验证完成 ===');
  },

  // 加载更多记录
  loadMoreRecords: function () {
    if (this.data.hasMore && !this.data.isLoading) {
      this.loadHistoryRecords(false);
    }
  },

  // 返回上一页
  navigateBack: function () {
    wx.navigateBack({
      delta: 1
    });
  },

  // 查看记录详情
  goToDetail: function (e) {
    const id = e.currentTarget.dataset.id;
    wx.navigateTo({
      url: `/pages/ocr/history/details/details?id=${id}`
    });
  },

  // 前往首页
  goToHome: function () {
    wx.navigateTo({
      url: '/pages/ocr/index/index'
    })
  },

  // 格式化时间显示
  formatTime: function (date, format = 'default') {
    if (!date) return '';

    if (typeof date === 'string') {
      date = new Date(date);
    }

    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hour = String(date.getHours()).padStart(2, '0');
    const minute = String(date.getMinutes()).padStart(2, '0');
    const second = String(date.getSeconds()).padStart(2, '0');

    switch (format) {
      case 'date':
        return `${year}-${month}-${day}`;
      case 'time':
        return `${hour}:${minute}:${second}`;
      case 'datetime':
        return `${year}-${month}-${day} ${hour}:${minute}:${second}`;
      case 'chinese':
        return `${year}年${month}月${day}日 ${hour}:${minute}`;
      default:
        return `${year}-${month}-${day} ${hour}:${minute}`;
    }
  },

  // 格式化日期时间显示
  formatDateTime: function (datetimeStr) {
    if (!datetimeStr) return '';
    try {
      const date = new Date(datetimeStr);
      return this.formatTime(date, 'chinese');
    } catch (e) {
      return datetimeStr;
    }
  },

  // 获取记录描述
  getRecordDescription: function (record) {
    if (!record.recognition_status) {
      return '识别失败，请重试';
    }

    const typeName = record.certificate_type_name || '';

    // 调试信息
    console.log('生成记录描述:', {
      typeName: typeName,
      hasVehicle: !!record.vehicle_result,
      hasIdCard: !!record.id_card_result,
      hasBusiness: !!record.business_result,
      vehicleResult: record.vehicle_result,
      idCardResult: record.id_card_result,
      businessResult: record.business_result
    });

    if (typeName.includes('行驶证') || record.vehicle_result) {
      const vehicle = record.vehicle_result || {};
      const number = vehicle.number || '未知';
      const owner = vehicle.owner_name || '未知';
      return `号牌: ${number} | 所有人: ${owner}`;
    } else if (typeName.includes('身份') || record.id_card_result) {
      const idCard = record.id_card_result || {};
      const name = idCard.name || '未知';
      const number = idCard.number ?
        (idCard.number.length > 10 ?
          idCard.number.substring(0, 6) + '****' + idCard.number.substring(14) :
          idCard.number) :
        '未知';
      return `姓名: ${name} | 证件号: ${number}`;
    } else if (typeName.includes('营业') || record.business_result) {
      const business = record.business_result || {};
      const name = business.name || '未知';
      const legalPerson = business.legal_representative || '未知';
      return `企业: ${name} | 法人: ${legalPerson}`;
    } else {
      // 通用描述
      const createdTime = new Date(record.created_at);
      const formattedTime = this.formatTime(createdTime, 'time');
      return `识别完成 ${formattedTime}`;
    }
  },

  // 调试函数：显示记录详细信息
  debugRecordInfo: function (record) {
    console.log('记录详细信息:', {
      id: record.id,
      certificate_type_name: record.certificate_type_name,
      has_vehicle_result: !!record.vehicle_result,
      has_id_card_result: !!record.id_card_result,
      has_business_result: !!record.business_result,
      vehicle_result: record.vehicle_result,
      id_card_result: record.id_card_result,
      business_result: record.business_result
    });
  }
});