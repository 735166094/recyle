import api from '../../../../config/settings.js'

Page({
  data: {
    recordDetail: null,
    isLoading: true,
    errorMessage: '',
    isLoggedIn: false,
    recordId: null,
    formattedResult: [],
    resultTitle: '识别详情'
  },

  onLoad: function (options) {
    console.log('详情页面加载，参数:', options);
    this.checkLoginStatus();
    if (options.id) {
      this.setData({
        recordId: options.id
      });
      this.loadRecordDetail(options.id);
    } else {
      this.setData({
        isLoading: false,
        errorMessage: '记录ID不存在'
      });
    }
  },

  onShow: function () {
    this.checkLoginStatus();
  },

  onPullDownRefresh: function () {
    if (this.data.recordId) {
      this.loadRecordDetail(this.data.recordId);
    }
    wx.stopPullDownRefresh();
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
        isLoggedIn: false
      });
      this.redirectToLogin();
      return false;
    }
  },

  // 跳转到登录页
  redirectToLogin: function () {
    wx.redirectTo({
      url: '/pages/login/login?redirect=' + encodeURIComponent('/pages/history/details/details?id=' + this.data.recordId)
    });
  },

  // 加载记录详情
loadRecordDetail: function (recordId) {
  const that = this;
  
  // 获取所有可能的Token
  const employeeToken = wx.getStorageSync('employeeToken');
  const token = wx.getStorageSync('token');

  console.log('Token详情:', {
    employeeToken: employeeToken ? `长度: ${employeeToken.length}, 前20位: ${employeeToken.substring(0, 20)}...` : '无',
    token: token ? `长度: ${token.length}, 前20位: ${token.substring(0, 20)}...` : '无'
  });

  // 确定使用哪个Token和Token类型
  let authToken = '';
  let tokenType = '';

  // 强制优先级：employeeToken > token
  if (employeeToken) {
    authToken = employeeToken;
    tokenType = 'Bearer';
    console.log('使用员工Token，类型: Bearer');
  } else if (token) {
    authToken = token;
    // 判断token类型
    if (authToken.startsWith('ey') && authToken.includes('.') && authToken.split('.').length === 3) {
      tokenType = 'Bearer';
      console.log('使用普通Token，类型: Bearer (JWT)');
    } else {
      tokenType = 'Token';
      console.log('使用普通Token，类型: Token');
    }
  }

  if (!authToken) {
    console.error('❌ 没有可用的Token');
    that.setData({
      isLoading: false,
      errorMessage: '请先登录'
    });
    wx.showToast({
      title: '请先登录',
      icon: 'none'
    });
    return;
  }

  this.setData({
    isLoading: true,
    errorMessage: ''
  });

  wx.request({
    url: api.records + recordId + '/',
    method: 'GET',
    header: {
      'Authorization': `${tokenType} ${authToken}`,
      'Content-Type': 'application/json'
    },
    success: function (res) {
      console.log('详情接口响应:', res);
      if (res.statusCode === 200) {
        that.processRecordData(res.data);
      } else if (res.statusCode === 401) {
        console.log('认证失败，清除本地存储并重试');
        // 清除所有可能存在的Token
        wx.removeStorageSync('employeeToken');
        wx.removeStorageSync('token');
        wx.removeStorageSync('user');
        wx.removeStorageSync('employeeInfo');
        
        that.setData({
          errorMessage: '登录已过期，请重新登录',
          isLoading: false
        });
        
        // 跳转到登录页
        setTimeout(() => {
          that.redirectToLogin();
        }, 1000);
      } else if (res.statusCode === 404) {
        that.setData({
          errorMessage: '记录不存在或已被删除',
          isLoading: false
        });
      } else {
        that.setData({
          errorMessage: `加载失败: ${res.statusCode}`,
          isLoading: false
        });
        wx.showToast({
          title: '加载记录失败',
          icon: 'none'
        });
      }
    },
    fail: function (err) {
      console.error('加载详情失败:', err);
      that.setData({
        errorMessage: '网络连接失败，请检查网络设置',
        isLoading: false
      });
      wx.showToast({
        title: '网络错误',
        icon: 'none'
      });
    }
  });
},

  // 处理记录数据
  processRecordData: function (recordData) {
    if (!recordData) {
      this.setData({
        isLoading: false,
        errorMessage: '记录数据为空'
      });
      return;
    }

    console.log('处理记录数据:', recordData);

    let formattedResult = [];
    let resultTitle = '识别详情';
    let hasValidData = false;

    // 基础信息
    const basicInfo = [{
        key: 'record_id',
        label: '记录ID',
        value: recordData.id
      },
      {
        key: 'status',
        label: '识别状态',
        value: recordData.recognition_status ? '成功' : '失败'
      },
      {
        key: 'create_time',
        label: '创建时间',
        value: recordData.created_at ? this.formatDateTime(recordData.created_at) : ''
      },
      {
        key: 'recognition_time',
        label: '识别时间',
        value: recordData.recognition_time ? this.formatDateTime(recordData.recognition_time) : ''
      }
    ].filter(item => item.value && item.value !== '');

    formattedResult.push(...basicInfo);

    // 根据不同的证件类型处理结果
    if (recordData.vehicle_result) {
      // 行驶证结果
      const vehicle = recordData.vehicle_result;
      resultTitle = '🚗 行驶证识别结果';

      const vehicleFields = [{
          key: 'number',
          label: '号牌号码',
          value: vehicle.number
        },
        {
          key: 'vehicle_type',
          label: '车辆类型',
          value: vehicle.vehicle_type
        },
        {
          key: 'owner_name',
          label: '所有人',
          value: vehicle.owner_name
        },
        {
          key: 'address',
          label: '地址',
          value: vehicle.address
        },
        {
          key: 'engine_no',
          label: '发动机号码',
          value: vehicle.engine_no
        },
        {
          key: 'vin',
          label: 'VIN码',
          value: vehicle.vin
        },
        {
          key: 'model',
          label: '品牌型号',
          value: vehicle.model
        },
        {
          key: 'register_date',
          label: '注册日期',
          value: vehicle.register_date
        },
        {
          key: 'issue_date',
          label: '发证日期',
          value: vehicle.issue_date
        },
        {
          key: 'use_character',
          label: '使用性质',
          value: vehicle.use_character
        }
      ].filter(item => item.value && item.value !== '未识别' && item.value !== '');

      formattedResult.push(...vehicleFields);
      hasValidData = vehicleFields.length > 0;

    } else if (recordData.id_card_result) {
      // 身份证结果
      const idCard = recordData.id_card_result;
      resultTitle = '🆔 身份证识别结果';

      const idCardFields = [{
          key: 'name',
          label: '姓名',
          value: idCard.name
        },
        {
          key: 'gender',
          label: '性别',
          value: idCard.gender
        },
        {
          key: 'ethnicity',
          label: '民族',
          value: idCard.ethnicity
        },
        {
          key: 'birth',
          label: '出生日期',
          value: idCard.birth
        },
        {
          key: 'address',
          label: '住址',
          value: idCard.address
        },
        {
          key: 'number',
          label: '身份证号码',
          value: idCard.number
        },
        {
          key: 'issue_authority',
          label: '签发机关',
          value: idCard.issue_authority
        },
        {
          key: 'valid_from',
          label: '有效期起始',
          value: idCard.valid_from
        },
        {
          key: 'valid_to',
          label: '有效期结束',
          value: idCard.valid_to
        }
      ].filter(item => item.value && item.value !== '未识别' && item.value !== '');

      formattedResult.push(...idCardFields);
      hasValidData = idCardFields.length > 0;

    } else if (recordData.business_result) {
      // 营业执照结果
      const business = recordData.business_result;
      resultTitle = '🏢 营业执照识别结果';

      const businessFields = [{
          key: 'name',
          label: '企业名称',
          value: business.name
        },
        {
          key: 'registration_number',
          label: '注册号',
          value: business.registration_number
        },
        {
          key: 'type',
          label: '企业类型',
          value: business.type
        },
        {
          key: 'address',
          label: '地址',
          value: business.address
        },
        {
          key: 'legal_representative',
          label: '法定代表人',
          value: business.legal_representative
        },
        {
          key: 'registered_capital',
          label: '注册资本',
          value: business.registered_capital
        },
        {
          key: 'found_date',
          label: '成立日期',
          value: business.found_date
        },
        {
          key: 'business_term',
          label: '营业期限',
          value: business.business_term
        },
        {
          key: 'business_scope',
          label: '经营范围',
          value: business.business_scope
        }
      ].filter(item => item.value && item.value !== '未识别' && item.value !== '');

      formattedResult.push(...businessFields);
      hasValidData = businessFields.length > 0;
    }

    // 显示使用的接口信息
    if (recordData.interface_used_name) {
      formattedResult.push({
        key: 'interface_used',
        label: '识别接口',
        value: recordData.interface_used_name
      });
    }

    if (recordData.certificate_type_name) {
      formattedResult.push({
        key: 'certificate_type',
        label: '证件类型',
        value: recordData.certificate_type_name
      });
    }

    if (!hasValidData && formattedResult.length <= basicInfo.length) {
      formattedResult.push({
        key: 'status_detail',
        label: '状态',
        value: '识别完成但未提取到有效信息'
      }, {
        key: 'suggestion',
        label: '建议',
        value: '请确保图片清晰、无反光，并包含完整的证件信息'
      });
    }

    this.setData({
      recordDetail: recordData,
      formattedResult: formattedResult,
      resultTitle: resultTitle,
      isLoading: false
    });

    console.log('详情数据处理完成:', {
      title: resultTitle,
      fields: formattedResult.length,
      hasValidData: hasValidData || formattedResult.length > basicInfo.length
    });
  },

  // 格式化时间
  formatDateTime: function (datetimeStr) {
    if (!datetimeStr) return '';
    try {
      const date = new Date(datetimeStr);
      const year = date.getFullYear();
      const month = String(date.getMonth() + 1).padStart(2, '0');
      const day = String(date.getDate()).padStart(2, '0');
      const hours = String(date.getHours()).padStart(2, '0');
      const minutes = String(date.getMinutes()).padStart(2, '0');
      const seconds = String(date.getSeconds()).padStart(2, '0');
      return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
    } catch (e) {
      console.error('时间格式化错误:', e);
      return datetimeStr;
    }
  },

  // 获取类型图标
  getTypeIcon: function (typeName) {
    if (!typeName) return '📄';
    if (typeName.includes('身份')) return '🆔';
    if (typeName.includes('行驶')) return '🚗';
    if (typeName.includes('营业')) return '🏢';
    if (typeName.includes('驾驶')) return '👮';
    return '📄';
  },

  // 返回上一页
  navBack: function () {
    wx.navigateBack({
      delta: 1
    });
  },

  // 复制结果
  copyResult: function () {
    const textToCopy = this.data.formattedResult.map(item =>
      `${item.label}：${item.value}`
    ).join('\n');

    if (!textToCopy.trim()) {
      wx.showToast({
        title: '无内容可复制',
        icon: 'none'
      });
      return;
    }

    wx.setClipboardData({
      data: textToCopy,
      success: function () {
        wx.showToast({
          title: '结果已复制到剪贴板',
          icon: 'success',
          duration: 2000
        });
      },
      fail: function () {
        wx.showToast({
          title: '复制失败',
          icon: 'none'
        });
      }
    });
  },

  // 保存结果
  saveResult: function () {
    wx.showToast({
      title: '记录已保存',
      icon: 'success',
      duration: 2000
    });
  },

  // 预览图片
  previewImage: function () {
    const imageUrl = this.data.recordDetail.image_url;
    if (imageUrl) {
      wx.previewImage({
        urls: [imageUrl],
        current: imageUrl
      });
    } else {
      wx.showToast({
        title: '图片不存在',
        icon: 'none'
      });
    }
  },

  // 删除记录
  deleteRecord: function () {
    const that = this;
    wx.showModal({
      title: '确认删除',
      content: '确定要删除这条记录吗？此操作不可恢复',
      confirmText: '删除',
      cancelText: '取消',
      confirmColor: '#ff4d4f',
      success: function (res) {
        if (res.confirm) {
          that.deleteRecordRequest();
        }
      }
    });
  },

  // 删除记录请求
  deleteRecordRequest: function () {
    const that = this;
    const token = wx.getStorageSync('token');

    wx.showLoading({
      title: '删除中...',
      mask: true
    });

    wx.request({
      url: api.records + that.data.recordId + '/',
      method: 'DELETE',
      header: {
        'Authorization': `Token ${token}`
      },
      success: function (res) {
        wx.hideLoading();
        if (res.statusCode === 204 || res.statusCode === 200) {
          wx.showToast({
            title: '删除成功',
            icon: 'success',
            duration: 1500
          });
          setTimeout(() => {
            wx.navigateBack();
          }, 1500);
        } else {
          wx.showToast({
            title: '删除失败',
            icon: 'none'
          });
        }
      },
      fail: function (err) {
        wx.hideLoading();
        console.error('删除记录失败:', err);
        wx.showToast({
          title: '删除失败，请重试',
          icon: 'none'
        });
      }
    });
  },

  // 重新识别
  reRecognize: function () {
    const that = this;
    const token = wx.getStorageSync('token');

    wx.showModal({
      title: '重新识别',
      content: '确定要重新识别这条记录吗？',
      confirmText: '重新识别',
      cancelText: '取消',
      success: function (res) {
        if (res.confirm) {
          that.reRecognizeRequest();
        }
      }
    });
  },

  // 重新识别请求
  reRecognizeRequest: function () {
    const that = this;
    const token = wx.getStorageSync('token');

    wx.showLoading({
      title: '重新识别中...',
      mask: true
    });

    wx.request({
      url: api.records + that.data.recordId + '/retry/',
      method: 'POST',
      header: {
        'Authorization': `Token ${token}`
      },
      success: function (res) {
        wx.hideLoading();
        if (res.statusCode === 200) {
          wx.showToast({
            title: '重新识别成功',
            icon: 'success'
          });
          // 重新加载详情
          that.loadRecordDetail(that.data.recordId);
        } else {
          wx.showToast({
            title: '重新识别失败',
            icon: 'none'
          });
        }
      },
      fail: function (err) {
        wx.hideLoading();
        console.error('重新识别失败:', err);
        wx.showToast({
          title: '重新识别失败，请重试',
          icon: 'none'
        });
      }
    });
  }
});