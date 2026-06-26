// pages/points/greenlife/greenlife.js 
const app = getApp();
const api = require('../../../config/settings');

Page({
  data: {
    // 绿色生活类型
    greenTypes: [{
        value: 'transport',
        name: '绿色出行',
        icon: 'transport',
        desc: '乘坐公交、地铁、共享单车等'
      },
      {
        value: 'food',
        name: '光盘行动',
        icon: 'food',
        desc: '用餐光盘，减少浪费'
      },
      {
        value: 'walk',
        name: '低碳行走',
        icon: 'walk',
        desc: '每日步数达标（1000步以上）'
      },
      {
        value: 'learning',
        name: '低碳学习',
        icon: 'learning',
        desc: '学习环保知识，获得证书'
      }
    ],

    selectedType: 'transport',
    selectedTypeInfo: null,

    // 表单数据
    formData: {
      green_type: 'transport',
      upload_image: null,
      certificate_image: null,
      steps_count: '',
      days_count: '1',
      description: ''
    },

    // 状态
    loading: false,
    submitting: false,
    todaySubmitted: false,
    todayPoints: 0,

    // 今日已提交记录
    submittedRecords: [],

    // 规则信息
    ruleInfo: null
  },

  onLoad(options) {
    const type = options.type || 'transport';
    this.setData({
      selectedType: type,
      'formData.green_type': type,
      selectedTypeInfo: this.getTypeInfo(type)
    });

    this.loadData();
  },

  onShow() {
    // 页面显示时重新检查
    this.checkTodaySubmit();
  },

  // 加载数据
  loadData() {
    this.setData({
      loading: true
    });

    Promise.all([
      this.getPointsRules(),
      this.checkTodaySubmit()
    ]).finally(() => {
      this.setData({
        loading: false
      });
    });
  },

  // 获取积分规则 
  async getPointsRules() {
    try {
      const response = await new Promise((resolve, reject) => {
        wx.request({
          url: api.pointsRules,
          method: 'GET',
          header: {
            'Authorization': app.globalData.token ? `Bearer ${app.globalData.token}` : '',
            'Content-Type': 'application/json'
          },
          success: resolve,
          fail: reject
        });
      });

      if (response.statusCode === 200 && response.data.code === 200) {
        // 找到当前类型的规则
        const rule = response.data.data.find(r => r.green_type === this.data.selectedType);
        if (rule) {
          this.setData({
            ruleInfo: rule
          });
        }
      }
    } catch (error) {
      console.error('获取规则失败:', error);
    }
  },

  // 检查今日是否已提交 - 使用正确的API端点
  async checkTodaySubmit() {
    try {
      const today = new Date().toISOString().split('T')[0];

      const response = await new Promise((resolve, reject) => {
        wx.request({
          url: api.pointsRecords,
          method: 'GET',
          data: {
            green_type: this.data.selectedType,
            date_from: today,
            date_to: today
          },
          header: {
            'Authorization': app.globalData.token ? `Bearer ${app.globalData.token}` : '',
            'Content-Type': 'application/json'
          },
          success: resolve,
          fail: reject
        });
      });

      if (response.statusCode === 200 && response.data.code === 200) {
        const records = response.data.data || [];
        if (records.length > 0) {
          const lastRecord = records[0];
          this.setData({
            todaySubmitted: true,
            todayPoints: lastRecord.points_change || 0,
            submittedRecords: records
          });
        } else {
          this.setData({
            todaySubmitted: false,
            todayPoints: 0,
            submittedRecords: []
          });
        }
      } else {
        this.setData({
          todaySubmitted: false,
          todayPoints: 0,
          submittedRecords: []
        });
      }
    } catch (error) {
      console.error('检查提交失败:', error);
      this.setData({
        todaySubmitted: false,
        todayPoints: 0,
        submittedRecords: []
      });
    }
  },

  // 获取类型信息
  getTypeInfo(type) {
    return this.data.greenTypes.find(t => t.value === type) || this.data.greenTypes[0];
  },

  // 选择类型
  onTypeSelect(e) {
    const type = e.currentTarget.dataset.type;
    const typeInfo = this.getTypeInfo(type);

    this.setData({
      selectedType: type,
      selectedTypeInfo: typeInfo,
      'formData.green_type': type,
      'formData.steps_count': '',
      'formData.days_count': '1',
      'formData.description': '',
      todaySubmitted: false
    });

    this.loadData();
  },

  // 选择图片
  chooseImage(field) {
    wx.chooseImage({
      count: 1,
      sizeType: ['compressed'],
      sourceType: ['album', 'camera'],
      success: (res) => {
        this.setData({
          [`formData.${field}`]: res.tempFilePaths[0]
        });
      }
    });
  },

  // 步数输入
  onStepsInput(e) {
    this.setData({
      'formData.steps_count': e.detail.value
    });
  },

  // 天数输入
  onDaysInput(e) {
    this.setData({
      'formData.days_count': e.detail.value || '1'
    });
  },

  // 描述输入
  onDescriptionInput(e) {
    this.setData({
      'formData.description': e.detail.value
    });
  },

  // 验证表单
  validateForm() {
    const {
      formData,
      selectedType
    } = this.data;

    if (!formData.green_type) {
      return {
        valid: false,
        message: '请选择绿色生活类型'
      };
    }

    if (selectedType === 'walk') {
      const steps = parseInt(formData.steps_count) || 0;
      if (steps < 1000) {
        return {
          valid: false,
          message: '步数需达到1000步以上'
        };
      }
      if (steps > 100000) {
        return {
          valid: false,
          message: '步数异常，请检查'
        };
      }
    }

    if (selectedType === 'transport' || selectedType === 'food') {
      if (!formData.upload_image) {
        return {
          valid: false,
          message: '请上传凭证图片'
        };
      }
    }

    if (selectedType === 'learning' && !formData.certificate_image) {
      return {
        valid: false,
        message: '请上传证书图片'
      };
    }

    return {
      valid: true,
      message: ''
    };
  },

  // 提交绿色生活记录
  async submitGreenLife() {
    if (this.data.todaySubmitted) {
      wx.showToast({
        title: '今日已提交过该类型',
        icon: 'none'
      });
      return;
    }

    // 验证表单
    const validation = this.validateForm();
    if (!validation.valid) {
      wx.showToast({
        title: validation.message,
        icon: 'none'
      });
      return;
    }

    this.setData({
      submitting: true
    });

    try {
      const {
        formData
      } = this.data;

      // 构建提交数据
      const submitData = {
        green_type: formData.green_type,
        description: formData.description || '',
        days_count: parseInt(formData.days_count) || 1
      };

      // 如果是walk类型，添加步数
      if (formData.green_type === 'walk') {
        submitData.steps_count = parseInt(formData.steps_count) || 0;
      }

      // 准备上传的文件
      const formDataToSend = new FormData();

      // 添加文本数据
      formDataToSend.append('green_type', submitData.green_type);
      formDataToSend.append('description', submitData.description);
      formDataToSend.append('days_count', submitData.days_count);

      if (formData.green_type === 'walk') {
        formDataToSend.append('steps_count', submitData.steps_count);
      }

      // 上传图片到服务器
      if (formData.upload_image) {
        await this.uploadAndAddToFormData(formData.upload_image, 'upload_image', formDataToSend);
      }

      if (formData.certificate_image) {
        await this.uploadAndAddToFormData(formData.certificate_image, 'certificate_image', formDataToSend);
      }

      // 调用API - 使用正确的绿色生活API端点
      const response = await new Promise((resolve, reject) => {
        wx.request({
          url: api.greenLife,
          method: 'POST',
          data: Object.fromEntries(formDataToSend.entries()),
          header: {
            'Authorization': app.globalData.token ? `Bearer ${app.globalData.token}` : '',
            'Content-Type': 'application/json'
          },
          success: resolve,
          fail: reject
        });
      });

      if (response.statusCode === 200) {
        const data = response.data;

        if (data.code === 200) {
          wx.showToast({
            title: '提交成功',
            icon: 'success',
            duration: 2000
          });

          // 显示获得的积分
          const points = data.data?.points || 0;

          setTimeout(() => {
            wx.showModal({
              title: '提交成功',
              content: `获得 ${points} 积分`,
              showCancel: false,
              confirmText: '知道了'
            });
          }, 1500);

          // 更新本地状态
          this.setData({
            todaySubmitted: true,
            todayPoints: points
          });

          // 更新用户信息中的积分
          if (app.globalData.userInfo) {
            app.globalData.userInfo.points = (app.globalData.userInfo.points || 0) + points;
            app.updateUserInfo(app.globalData.userInfo);
          }
        } else {
          throw new Error(data.message || '提交失败');
        }
      } else if (response.statusCode === 400) {
        wx.showToast({
          title: response.data?.message || '提交失败',
          icon: 'none'
        });
      } else if (response.statusCode === 401) {
        wx.showToast({
          title: '请重新登录',
          icon: 'none'
        });
        wx.navigateTo({
          url: '/pages/user/login/login'
        });
      } else {
        throw new Error(`请求失败，状态码：${response.statusCode}`);
      }

    } catch (error) {
      console.error('提交失败:', error);
      wx.showToast({
        title: error.message || '提交失败',
        icon: 'none'
      });
    } finally {
      this.setData({
        submitting: false
      });
    }
  },

  // 上传图片到服务器并添加到表单数据
  async uploadAndAddToFormData(filePath, fieldName, formData) {
    return new Promise((resolve, reject) => {
      wx.uploadFile({
        url: 'http://192.168.5.46:8000/recycle/api/upload/image/', // 使用正确的上传接口
        filePath: filePath,
        name: fieldName,
        formData: {
          'upload_type': 'green_life'
        },
        header: {
          'Authorization': app.globalData.token ? `Bearer ${app.globalData.token}` : ''
        },
        success: (res) => {
          try {
            const data = JSON.parse(res.data);
            if (data.code === 200 && data.data && data.data.url) {
              // 将图片URL添加到表单数据中
              formData.append(fieldName, data.data.url);
              resolve();
            } else {
              reject(new Error(data.message || '图片上传失败'));
            }
          } catch (e) {
            reject(e);
          }
        },
        fail: reject
      });
    });
  },

  // 查看规则详情
  viewRuleDetail() {
    if (!this.data.ruleInfo) return;

    wx.showModal({
      title: this.data.selectedTypeInfo.name,
      content: this.data.ruleInfo.description || '暂无详细说明',
      showCancel: false,
      confirmText: '知道了'
    });
  },

  // 查看今日记录
  viewTodayRecords() {
    if (this.data.submittedRecords.length === 0) return;

    const records = this.data.submittedRecords;
    let content = '';

    records.forEach((record, index) => {
      content += `${index + 1}. ${this.formatDateTime(record.created_at)} - 获得 ${record.points_change || 0} 积分\n`;
      if (record.description) {
        content += `   ${record.description}\n`;
      }
      content += '\n';
    });

    wx.showModal({
      title: '今日提交记录',
      content: content,
      showCancel: false,
      confirmText: '知道了'
    });
  },

  // 格式化时间
  formatDateTime(dateTimeStr) {
    if (!dateTimeStr) return '';

    try {
      const date = new Date(dateTimeStr);
      return `${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`;
    } catch (e) {
      return dateTimeStr;
    }
  },

  // 返回
  goBack() {
    wx.navigateBack();
  }
});