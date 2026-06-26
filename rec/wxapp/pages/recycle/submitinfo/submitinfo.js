// pages/recycle/submitinfo/submitinfo.js
const api = require('../../../config/settings.js')

Page({

  /**
   * 页面的初始数据
   */
  data: {
    imageUrl: '', // 上传的图片路径
    tempImagePath: '', // 临时图片路径
    region: [], // 地区选择
    uploading: false, // 图片上传状态
    submitting: false, // 表单提交状态
    choosingLocation: false, // 选择位置状态
    focusedField: '', // 当前聚焦的字段
    showSuccessModal: false, // 显示成功弹窗
    formData: {
      contactName: '',
      contactPhone: '',
      address: '',
      carModel: '',
      carCount: 1,
      wheelType: '',
      wheelCount: 0,
      ternaryCount: 0,
      batteryCount: 0,
      batteryPackCount: 0,
      engineCount: 0,
      weight: null,
      canStart: true,
      remark: ''
    },
    savedImagePath: '', // 服务器保存的图片路径

    // 重新提交相关
    isResubmit: false,
    originalRecordId: null,
  },

  /**
   * 生命周期函数--监听页面加载
   */
  onLoad(options) {
    console.log('提交页面加载，参数:', options)

    // 首先检查用户登录状态
    const isLoggedIn = this.checkLoginStatus();
    console.log("登陆状态：", isLoggedIn)

    if (!isLoggedIn) {
      // 未登录，跳转到登录页面，并传递当前页面路径作为重定向参数
      const pages = getCurrentPages();
      const currentPage = pages[pages.length - 1];
      let queryString = '';

      // 如果有页面参数，构造查询字符串
      if (options && Object.keys(options).length > 0) {
        const params = [];
        for (let key in options) {
          params.push(`${key}=${options[key]}`);
        }
        queryString = params.join('&');
      }

      // 构造当前页面路径
      const currentPath = `/pages/recycle/submitinfo/submitinfo${queryString ? '?' + queryString : ''}`;

      console.log('[SubmitInfo] 未登录，跳转到登录页面，重定向路径:', currentPath);

      wx.redirectTo({
        url: `/pages/user/login/login?redirect=${encodeURIComponent(currentPath)}`,
        success: () => {
          console.log('[SubmitInfo] 跳转到登录页面成功');
        },
        fail: (err) => {
          console.error('[SubmitInfo] 跳转到登录页面失败:', err);
          // 跳转失败，显示提示
          wx.showToast({
            title: '请先登录',
            icon: 'none',
            duration: 2000
          });
        }
      });
      return; // 停止执行后续代码
    }

    // 打印全局数据
    const app = getApp();
    console.log('全局数据:', {
      token: app.globalData.token,
      userInfo: app.globalData.userInfo,
      isLoggedIn: app.globalData.isLoggedIn
    });

    // 打印本地存储
    console.log('本地存储token:', wx.getStorageSync('token'));
    console.log('本地存储userInfo:', wx.getStorageSync('userInfo'));


    // 已登录，继续原有逻辑
    this.getUserInfo();
    this.initLocation();

    // 检查是否是重新提交操作
    if (options.action === 'resubmit') {
      this.handleResubmitData();
    }
  },

  /**
   * 检查用户登录状态
   */
  checkLoginStatus() {
    const app = getApp();

    // 检查全局登录状态
    if (app.globalData && app.globalData.isLoggedIn) {
      console.log('[SubmitInfo] 全局状态显示已登录');
      return true;
    }

    // 检查本地存储的token
    const token = wx.getStorageSync('token');
    if (token) {
      console.log('[SubmitInfo] 本地存储有token');

      // 如果有token但全局状态未更新，更新全局状态
      if (app.globalData) {
        app.globalData.isLoggedIn = true;
        app.globalData.token = token;

        // 尝试获取用户信息
        const userInfo = wx.getStorageSync('userInfo');
        if (userInfo) {
          app.globalData.userInfo = userInfo;
        }
      }
      return true;
    }

    console.log('[SubmitInfo] 用户未登录');
    return false;
  },

  // 处理重新提交数据
  handleResubmitData() {
    const resubmitData = wx.getStorageSync('resubmitData')
    const isResubmit = wx.getStorageSync('isResubmit')

    if (resubmitData && isResubmit) {
      console.log('检测到重新提交数据:', resubmitData)

      // 填充表单数据
      this.setData({
        'formData.contactName': resubmitData.contactName || '',
        'formData.contactPhone': resubmitData.contactPhone || '',
        'formData.address': resubmitData.address || '',
        'formData.carModel': resubmitData.carModel || '',
        'formData.carCount': resubmitData.carCount || 1,
        'formData.wheelType': resubmitData.wheelType || '',
        'formData.wheelCount': resubmitData.wheelCount || 0,
        'formData.ternaryCount': resubmitData.ternaryCount || 0,
        'formData.batteryCount': resubmitData.batteryCount || 0,
        'formData.batteryPackCount': resubmitData.batteryPackCount || 0,
        'formData.engineCount': resubmitData.engineCount || 0,
        'formData.weight': resubmitData.weight || '',
        'formData.canStart': resubmitData.canStart !== undefined ? resubmitData.canStart : true,
        'formData.remark': resubmitData.remark || '',
        region: resubmitData.region || [],
        imageUrl: resubmitData.carImageUrl || '',
        savedImagePath: resubmitData.carImagePath || '',
        isResubmit: true,
        originalRecordId: resubmitData.originalRecordId
      })

      // 显示提示信息
      wx.showToast({
        title: '原记录数据已加载',
        icon: 'success',
        duration: 2000
      })

      // 清理缓存数据
      wx.removeStorageSync('resubmitData')
      wx.removeStorageSync('isResubmit')
    }
  },

  /**
   * 获取用户信息并自动填充
   */
  getUserInfo() {
    const app = getApp();
    if (app.globalData.userInfo) {
      this.autoFillUserInfo(app.globalData.userInfo);
    } else {
      // 如果没有用户信息，尝试从缓存获取
      const userInfo = wx.getStorageSync('userInfo');
      if (userInfo) {
        this.autoFillUserInfo(userInfo);
      } else {
        // 调用用户信息接口
        this.fetchUserProfile();
      }
    }
  },

  /**
   * 调用接口获取用户信息
   */
  fetchUserProfile() {
    const app = getApp();
    const token = app.globalData.token;

    if (!token) {
      return;
    }

    wx.request({
      url: api.userProfile,
      method: 'GET',
      header: {
        'Authorization': `Bearer ${token}`
      },
      success: (res) => {
        if (res.data.code === 200 && res.data.data) {
          this.autoFillUserInfo(res.data.data);
          // 更新全局用户信息
          app.globalData.userInfo = res.data.data;
          wx.setStorageSync('userInfo', res.data.data);
        }
      },
      fail: (err) => {
        console.error('获取用户信息失败:', err);
      }
    });
  },

  /**
   * 自动填充用户信息
   */
  autoFillUserInfo(userInfo) {
    console.log('获取到的用户信息:', userInfo);
    console.log('手机号字段 phone:', userInfo.phone);
    console.log('真实姓名字段 real_name:', userInfo.real_name);
    console.log('昵称字段 nickname:', userInfo.nickname);

    const formData = {
      contactName: userInfo.real_name || userInfo.nickname || '',
      contactPhone: userInfo.phone || '',
      address: '',
      carModel: '',
      carCount: 1,
      wheelType: '',
      wheelCount: 0,
      ternaryCount: 0,
      batteryCount: 0,
      batteryPackCount: 0,
      engineCount: 0,
      weight: null,
      canStart: true,
      remark: ''
    };

    console.log('自动填充的表单数据:', formData);

    this.setData({
      formData: formData
    });
  },

  /**
   * 初始化位置信息
   */
  initLocation() {
    // 尝试从缓存获取上次的位置信息
    const lastLocation = wx.getStorageSync('lastLocation');
    if (lastLocation && lastLocation.region) {
      this.setData({
        region: lastLocation.region
      });
    }
  },

  /**
   * 使用微信地图选择位置  
   */
  chooseLocation() {
    const that = this;

    // 检查位置权限
    wx.getSetting({
      success: (res) => {
        if (res.authSetting['scope.userLocation'] === undefined) {
          // 首次使用，请求授权
          that.requestLocationPermission();
        } else if (res.authSetting['scope.userLocation']) {
          // 已授权，尝试打开地图选择位置
          that.tryOpenLocationPicker();
        } else {
          // 已拒绝授权，提供替代方案
          that.showLocationAlternative();
        }
      },
      fail: () => {
        that.tryOpenLocationPicker();
      }
    });
  },

  /**
   * 请求定位权限
   */
  requestLocationPermission() {
    const that = this;

    wx.authorize({
      scope: 'scope.userLocation',
      success: () => {
        that.tryOpenLocationPicker();
      },
      fail: () => {
        that.showLocationAlternative();
      }
    });
  },

  /**
   * 尝试打开地图选择位置
   */
  tryOpenLocationPicker() {
    const that = this;

    that.setData({
      choosingLocation: true
    });

    // 尝试使用 chooseLocation
    wx.chooseLocation({
      success: (res) => {
        console.log('选择的位置信息:', res);
        that.handleLocationSuccess(res);
      },
      fail: (err) => {
        console.error('chooseLocation失败:', err);

        // 如果 chooseLocation 失败，尝试使用 getLocation 获取当前位置
        that.fallbackToGetLocation();
      },
      complete: () => {
        that.setData({
          choosingLocation: false
        });
      }
    });
  },

  /**
   * 处理位置选择成功
   */
  handleLocationSuccess(locationInfo) {
    const that = this;
    const address = locationInfo.address;
    const name = locationInfo.name;

    // 解析地址信息
    const parsedAddress = that.parseAddressFromText(address || name || '');

    if (parsedAddress.province && parsedAddress.city && parsedAddress.district) {
      // 设置地区选择器和详细地址
      that.setData({
        region: [parsedAddress.province, parsedAddress.city, parsedAddress.district],
        'formData.address': address || name || ''
      });

      // 保存位置信息到缓存
      wx.setStorageSync('lastLocation', {
        region: [parsedAddress.province, parsedAddress.city, parsedAddress.district],
        address: address || name || ''
      });

      wx.showToast({
        title: '位置选择成功',
        icon: 'success',
        duration: 1500
      });
    } else {
      // 如果解析不完整，让用户手动选择地区
      that.setData({
        'formData.address': address || name || ''
      });

      wx.showModal({
        title: '提示',
        content: '已获取到详细地址，请在地区选择器中手动选择省市区',
        showCancel: false,
        success: () => {
          // 用户可以手动选择地区
        }
      });
    }
  },

  /**
   * 回退方案：使用 getLocation 获取当前位置
   */
  fallbackToGetLocation() {
    const that = this;

    wx.getLocation({
      type: 'gcj02',
      success: (locationRes) => {
        // 使用逆地理编码获取地址信息
        that.reverseGeocode(locationRes.latitude, locationRes.longitude);
      },
      fail: (err) => {
        console.error('getLocation失败:', err);
        that.showLocationAlternative();
      }
    });
  },

  /**
   * 显示位置选择的替代方案
   */
  showLocationAlternative() {
    const that = this;

    wx.showModal({
      title: '位置服务',
      content: '为了提供更准确的服务，建议您授权位置权限。您也可以手动选择地区或在详细地址中填写完整地址。',
      confirmText: '去授权',
      cancelText: '手动填写',
      success: (res) => {
        if (res.confirm) {
          // 引导用户去设置页面授权
          wx.openSetting({
            success: (settingRes) => {
              if (settingRes.authSetting['scope.userLocation']) {
                that.tryOpenLocationPicker();
              } else {
                wx.showToast({
                  title: '未授权位置权限',
                  icon: 'none',
                  duration: 2000
                });
              }
            }
          });
        } else {
          // 用户选择手动填写，显示提示
          wx.showToast({
            title: '请在地区选择器中选择省市区',
            icon: 'none',
            duration: 2000
          });
        }
      }
    });
  },

  /**
   * 从文本中解析地址信息
   */
  parseAddressFromText(addressText) {
    let province = '';
    let city = '';
    let district = '';

    if (!addressText) {
      return {
        province,
        city,
        district
      };
    }

    // 简单的地址解析逻辑
    const address = addressText;

    // 匹配省份
    const provinceRegex = /(北京市|天津市|上海市|重庆市|河北省|山西省|辽宁省|吉林省|黑龙江省|江苏省|浙江省|安徽省|福建省|江西省|山东省|河南省|湖北省|湖南省|广东省|海南省|四川省|贵州省|云南省|陕西省|甘肃省|青海省|台湾省|内蒙古自治区|广西壮族自治区|西藏自治区|宁夏回族自治区|新疆维吾尔自治区|香港特别行政区|澳门特别行政区)/;
    const provinceMatch = address.match(provinceRegex);
    if (provinceMatch) {
      province = provinceMatch[1];
    }

    // 匹配城市（排除省份部分）
    let remainingAddress = address;
    if (province) {
      remainingAddress = address.replace(province, '');
    }

    const cityRegex = /(.*?[市|地区|自治州|盟])/;
    const cityMatch = remainingAddress.match(cityRegex);
    if (cityMatch) {
      city = cityMatch[1].trim();
    }

    // 匹配区县（排除省市级部分）
    if (province && city) {
      remainingAddress = remainingAddress.replace(city, '');
    }

    const districtRegex = /(.*?[区|县|市|旗])/;
    const districtMatch = remainingAddress.match(districtRegex);
    if (districtMatch) {
      district = districtMatch[1].trim();
    }

    // 特殊处理直辖市
    if (['北京市', '天津市', '上海市', '重庆市'].includes(province)) {
      city = province; // 直辖市市级就是省级
      // 在直辖市中，第一个区县就是区级
      if (!district && cityMatch) {
        district = cityMatch[1].trim();
      }
    }

    return {
      province,
      city,
      district
    };
  },

  /**
   * 逆地理编码，将经纬度转换为地址
   */
  reverseGeocode(latitude, longitude) {
    const that = this;

    // 显示加载提示
    wx.showLoading({
      title: '解析地址中...',
      mask: true
    });

    // 由于微信小程序限制，这里使用模拟数据
    // 在实际项目中，可以调用自己的后端服务进行逆地理编码
    setTimeout(() => {
      wx.hideLoading();

      // 模拟解析结果
      const mockAddress = "北京市朝阳区望京街道";
      const parsedAddress = that.parseAddressFromText(mockAddress);

      if (parsedAddress.province && parsedAddress.city && parsedAddress.district) {
        that.setData({
          region: [parsedAddress.province, parsedAddress.city, parsedAddress.district],
          'formData.address': mockAddress
        });

        wx.showToast({
          title: '定位成功',
          icon: 'success',
          duration: 1500
        });
      } else {
        that.showLocationAlternative();
      }
    }, 1500);
  },

  /**
   * 显示上传操作菜单
   */
  showUploadAction() {
    // 再次检查登录状态（双重保障）
    if (!this.checkLoginStatus()) {
      wx.showToast({
        title: '请先登录',
        icon: 'none',
        duration: 2000,
        success: () => {
          setTimeout(() => {
            wx.redirectTo({
              url: '/pages/user/login/login?redirect=/pages/recycle/submitinfo/submitinfo'
            });
          }, 1500);
        }
      });
      return;
    }

    wx.showActionSheet({
      itemList: ['拍照', '从相册选择'],
      success: (res) => {
        const tapIndex = res.tapIndex;
        if (tapIndex === 0) {
          this.takePhoto();
        } else if (tapIndex === 1) {
          this.chooseImageFromAlbum();
        }
      },
      fail: (err) => {
        console.error('显示操作菜单失败:', err);
      }
    });
  },

  /**
   * 拍照 
   */
  takePhoto() {
    const that = this;

    // 检查相机权限
    wx.authorize({
      scope: 'scope.camera',
      success: () => {
        // 用户已经授权，直接调用相机
        that.openCamera();
      },
      fail: (err) => {
        console.log('未授权相机权限:', err);
        // 引导用户授权
        wx.showModal({
          title: '提示',
          content: '需要访问您的相机权限，是否前往设置开启？',
          confirmText: '去设置',
          success: (res) => {
            if (res.confirm) {
              wx.openSetting({
                success: (settingRes) => {
                  if (settingRes.authSetting['scope.camera']) {
                    that.openCamera();
                  } else {
                    wx.showToast({
                      title: '未授权相机权限',
                      icon: 'none'
                    });
                  }
                }
              });
            }
          }
        });
      }
    });
  },

  /**
   * 打开相机拍照
   */
  openCamera() {
    const that = this;

    wx.chooseMedia({
      count: 1,
      mediaType: ['image'],
      sourceType: ['camera'],
      maxDuration: 30,
      camera: 'back',
      success: (res) => {
        if (res.tempFiles && res.tempFiles.length > 0) {
          const tempFilePath = res.tempFiles[0].tempFilePath;

          // 直接使用照片，不需要预览确认
          that.setData({
            uploading: true
          });

          // 上传图片
          that.uploadImage(tempFilePath);
        }
      },
      fail: (err) => {
        console.error('拍照失败:', err);
        wx.showToast({
          title: '拍照失败，请重试',
          icon: 'none'
        });
      }
    });
  },

  /**
   * 从相册选择
   */
  chooseImageFromAlbum() {
    wx.chooseMedia({
      count: 1,
      mediaType: ['image'],
      sourceType: ['album'],
      success: (res) => {
        if (res.tempFiles && res.tempFiles.length > 0) {
          const tempFilePath = res.tempFiles[0].tempFilePath;
          this.setData({
            uploading: true
          });
          this.uploadImage(tempFilePath);
        }
      },
      fail: (err) => {
        console.error('选择图片失败:', err);
        this.setData({
          uploading: false
        });
        wx.showToast({
          title: '选择图片失败',
          icon: 'none'
        });
      }
    });
  },

  /**
   * 预览图片
   */
  previewImage(e) {
    const src = e.currentTarget.dataset.src;
    if (src) {
      wx.previewImage({
        urls: [src],
        current: src
      });
    }
  },

  /**
   * 上传图片到服务器
   */
  uploadImage(tempFilePath) {
    const app = getApp();
    const token = app.globalData.token;

    if (!token) {
      wx.showToast({
        title: '请先登录',
        icon: 'none',
        success: () => {
          setTimeout(() => {
            wx.navigateTo({
              url: '/pages/user/login/login'
            });
          }, 1500);
        }
      });
      return;
    }

    wx.showLoading({
      title: '上传图片中...',
      mask: true
    });

    // 先显示本地图片
    this.setData({
      imageUrl: tempFilePath,
      tempImagePath: tempFilePath,
      uploading: true
    });

    // 1. 先获取图片信息
    wx.getImageInfo({
      src: tempFilePath,
      success: (imageInfo) => {
        // 2. 压缩图片，控制大小在2MB以内
        const compressOptions = {
          src: tempFilePath,
          quality: 70, // 压缩质量，范围0-100
          success: (compressRes) => {
            console.log('压缩成功，压缩后路径:', compressRes.tempFilePath);

            // 3. 上传压缩后的图片
            this.uploadCompressedImage(compressRes.tempFilePath, token);
          },
          fail: (compressErr) => {
            console.error('图片压缩失败:', compressErr);
            wx.hideLoading();
            this.setData({
              uploading: false
            });
            wx.showToast({
              title: '图片处理失败，请重试',
              icon: 'none'
            });
          }
        };

        // 根据原图大小调整压缩比例
        if (imageInfo.width > 2000 || imageInfo.height > 2000) {
          // 大图片，使用更高的压缩率
          compressOptions.quality = 60;
        }

        wx.compressImage(compressOptions);
      },
      fail: (err) => {
        console.error('获取图片信息失败:', err);
        wx.hideLoading();
        this.setData({
          uploading: false
        });
        wx.showToast({
          title: '图片信息获取失败',
          icon: 'none'
        });
      }
    });
  },

  /**
   * 修复后的上传方法 
   */
  uploadCompressedImage(compressedFilePath, token) {
    const that = this;

    console.log('开始上传图片，服务器地址:', api.carImageUpload);
    console.log('Token长度:', token ? token.length : 0);

    // 添加上传任务ID，用于调试
    const uploadTaskId = Date.now();
    console.log(`上传任务 ${uploadTaskId} 开始`);

    const uploadTask = wx.uploadFile({
      url: api.carImageUpload,
      filePath: compressedFilePath,
      name: 'image',
      header: {
        'Authorization': `Bearer ${token}`,
        'X-Request-ID': uploadTaskId,
        'Accept': 'application/json'
      },
      formData: {
        'platform': 'miniprogram',
        'version': '1.0.0'
      },
      timeout: 60000, // 生产环境适当延长超时时间

      success: (res) => {
        console.log(`上传任务 ${uploadTaskId} 成功:`, {
          statusCode: res.statusCode,
          dataLength: res.data ? res.data.length : 0,
          preview: res.data ? res.data.substring(0, 100) : '无数据'
        });

        // 处理响应
        that.handleUploadResponse(res);
      },

      fail: (err) => {
        console.error(`上传任务 ${uploadTaskId} 失败:`, err);

        // 详细分析错误类型
        let errorMsg = '网络错误，请检查网络连接';

        if (err.errMsg.includes('timeout')) {
          errorMsg = '上传超时，请检查网络后重试';
        } else if (err.errMsg.includes('fail') && err.errMsg.includes('url')) {
          errorMsg = '服务器地址错误，请联系管理员';
        } else if (err.errMsg.includes('fail') && err.errMsg.includes('token')) {
          errorMsg = '登录已过期，请重新登录';
          // 跳转登录
          setTimeout(() => {
            wx.redirectTo({
              url: '/pages/user/login/login'
            });
          }, 1500);
        }

        wx.showToast({
          title: errorMsg,
          icon: 'none',
          duration: 3000
        });

        that.setData({
          uploading: false
        });
      }
    });

    // 监听上传进度
    uploadTask.onProgressUpdate((res) => {
      console.log(`上传进度 ${uploadTaskId}:`, res.progress + '%');
    });

    // 保存uploadTask，可以在需要时取消
    that.currentUploadTask = uploadTask;
  },

  /**
   * 处理上传响应
   */
  handleUploadResponse(res) {
    const that = this;

    // 2xx状态码都表示成功
    if (res.statusCode >= 200 && res.statusCode < 300) {
      try {
        const result = JSON.parse(res.data);

        // 检查是否真的成功
        if (result.success || result.code === 200 || result.code === 201) {
          that.setData({
            imageUrl: result.image_url || result.data?.url || that.data.tempImagePath,
            uploading: false,
            savedImagePath: result.saved_path || result.data?.path || ''
          });

          wx.showToast({
            title: '图片上传成功',
            icon: 'success',
            duration: 2000
          });

          console.log('图片上传成功，保存路径:', that.data.savedImagePath);
        } else {
          // 业务逻辑失败
          that.setData({
            uploading: false
          });
          wx.showToast({
            title: result.message || result.error || '上传失败',
            icon: 'none',
            duration: 2000
          });
        }
      } catch (e) {
        console.error('解析响应失败:', e);
        that.setData({
          uploading: false
        });
        wx.showToast({
          title: '服务器响应格式错误',
          icon: 'none',
          duration: 2000
        });
      }
    } else {
      // 非2xx状态码
      that.setData({
        uploading: false
      });
      wx.showToast({
        title: `服务器错误 (${res.statusCode})`,
        icon: 'none',
        duration: 2000
      });
    }
  },

  /**
   * 删除图片
   */
  deleteImage() {
    wx.showModal({
      title: '提示',
      content: '确定要删除这张图片吗？',
      success: (res) => {
        if (res.confirm) {
          this.setData({
            imageUrl: '',
            tempImagePath: '',
            savedImagePath: ''
          });
        }
      }
    });
  },

  /**
   * 表单输入处理
   */
  onInputChange(e) {
    const field = e.currentTarget.dataset.field;
    let value = e.detail.value;

    // 根据字段类型进行数据转换
    if (field.includes('Count') || field === 'weight') {
      value = value ? parseInt(value) || 0 : 0;
      if (field === 'weight' && value === 0) {
        value = null; // weight 字段可以为 null
      }
    } else if (field === 'canStart') {
      value = value === 'true';
    }

    this.setData({
      [`formData.${field}`]: value
    });
  },

  /**
   * 格式化手机号
   */
  formatPhone(e) {
    let value = e.detail.value;
    // 去除非数字字符
    value = value.replace(/\D/g, '');
    // 限制长度为11位
    if (value.length > 11) {
      value = value.substring(0, 11);
    }
    // 更新输入框值
    this.setData({
      [`formData.contactPhone`]: value
    });
    return value;
  },

  /**
   * 地区选择变化
   */
  onRegionChange(e) {
    const selectedRegion = e.detail.value;
    this.setData({
      region: selectedRegion
    });

    // 保存地区信息到缓存
    wx.setStorageSync('lastLocation', {
      region: selectedRegion,
      address: this.data.formData.address
    });
  },

  /**
   * 输入框聚焦
   */
  onInputFocus(e) {
    this.setData({
      focusedField: e.currentTarget.dataset.name || ''
    });
  },

  /**
   * 输入框失焦
   */
  onInputBlur() {
    this.setData({
      focusedField: ''
    });
  },

  /**
   * 显示成功弹窗
   */
  showSuccessModal() {
    this.setData({
      showSuccessModal: true
    });
  },

  /**
   * 隐藏成功弹窗
   */
  hideSuccessModal() {
    this.setData({
      showSuccessModal: false
    });
    // 跳转到记录页面
    setTimeout(() => {
      wx.redirectTo({
        url: '/pages/recycle/record/record',
        fail: (err) => {
          console.error('跳转记录页失败', err);
          // 跳转失败时 fallback 到首页
          wx.switchTab({
            url: '/pages/index/index'
          });
        }
      });
    }, 300);
  },

  /**
   * 表单提交
   */
  formSubmit(e) {
    const formData = e.detail.value;
    console.log('表单数据:', formData);

    // 检查登录状态
    if (!this.checkLoginStatus()) {
      wx.showModal({
        title: '提示',
        content: '提交信息需要先登录，是否立即登录？',
        success: (res) => {
          if (res.confirm) {
            const pages = getCurrentPages();
            const currentPage = pages[pages.length - 1];
            const route = currentPage.route;
            const options = currentPage.options;

            let queryString = '';
            if (options && Object.keys(options).length > 0) {
              const params = [];
              for (let key in options) {
                params.push(`${key}=${options[key]}`);
              }
              queryString = params.join('&');
            }

            const currentPath = `/${route}${queryString ? '?' + queryString : ''}`;

            wx.redirectTo({
              url: `/pages/user/login/login?redirect=${encodeURIComponent(currentPath)}`
            });
          }
        }
      });
      return;
    }

    // 阻止重复提交
    if (this.data.submitting) {
      return;
    }

    // 验证表单数据
    const validation = this.validateForm(formData);
    if (!validation.valid) {
      wx.showToast({
        title: validation.msg,
        icon: 'none',
        duration: 2000
      });
      return;
    }

    // 验证地区选择
    if (!this.data.region || this.data.region.length !== 3) {
      wx.showToast({
        title: '请选择完整的省市区',
        icon: 'none',
        duration: 2000
      });
      return;
    }

    // 验证图片
    if (!this.data.savedImagePath) {
      wx.showToast({
        title: '请上传车辆照片',
        icon: 'none',
        duration: 2000
      });
      return;
    }

    // 开始提交
    this.setData({
      submitting: true
    });

    wx.showLoading({
      title: '提交中...',
      mask: true
    });

    // 构建提交数据
    const submitData = {
      contact_name: formData.contactName,
      contact_phone: formData.contactPhone,
      region: this.data.region.join(' '), // 将数组转换为字符串
      address: formData.address,
      car_model: formData.carModel,
      car_count: parseInt(formData.carCount) || 1,
      wheel_type: formData.wheelType || '',
      wheel_count: parseInt(formData.wheelCount) || 0,
      ternary_count: parseInt(formData.ternaryCount) || 0,
      battery_count: parseInt(formData.batteryCount) || 0,
      battery_pack_count: parseInt(formData.batteryPackCount) || 0,
      engine_count: parseInt(formData.engineCount) || 0,
      weight: formData.weight ? parseInt(formData.weight) : null,
      can_start: formData.canStart === 'true' || formData.canStart === true,
      car_image_path: this.data.savedImagePath, // 使用服务器返回的图片路径
      remark: formData.remark || ''
    };

    console.log('提交到服务器的数据:', submitData);

    // 提交到服务器
    this.submitToServer(submitData);
  },

  /**
   * 验证表单数据
   */
  validateForm(formData) {
    // 验证联系人姓名
    if (!formData.contactName || formData.contactName.trim() === '') {
      return {
        valid: false,
        msg: '请输入联系人姓名'
      };
    }

    // 验证联系电话
    const phone = formData.contactPhone;
    if (!phone || phone.length !== 11 || !/^1[3-9]\d{9}$/.test(phone)) {
      return {
        valid: false,
        msg: '请输入正确的11位手机号码'
      };
    }

    // 验证车型
    if (!formData.carModel || formData.carModel.trim() === '') {
      return {
        valid: false,
        msg: '请输入车型信息'
      };
    }

    // 验证车辆数量
    const carCount = parseInt(formData.carCount);
    if (isNaN(carCount) || carCount < 1) {
      return {
        valid: false,
        msg: '车辆数量至少为1'
      };
    }

    // 验证整备质量（如果填写）
    if (formData.weight) {
      const weight = parseInt(formData.weight);
      if (isNaN(weight) || weight < 500 || weight > 5000) {
        return {
          valid: false,
          msg: '整备质量应在500-5000千克之间'
        };
      }
    }

    return {
      valid: true
    };
  },

  /**
   * 提交数据到服务器
   */
  submitToServer(submitData) {
    const app = getApp();
    const token = app.globalData.token;

    console.log('请求URL:', api.scrapCarRecords);
    console.log('请求Token:', token ? '有token' : '无token');
    console.log('请求数据:', submitData);

    wx.request({
      url: api.scrapCarRecords,
      method: 'POST',
      header: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      data: submitData,
      success: (res) => {
        console.log('响应状态码:', res.statusCode);
        console.log('响应数据:', res.data);
        wx.hideLoading();

        if (res.statusCode === 201) {
          if (res.data.success) {
            // 提交成功 - 使用自定义弹窗
            this.showSuccessModal();
          } else {
            // 业务逻辑失败
            this.setData({
              submitting: false
            });
            wx.showToast({
              title: res.data.message || '提交失败',
              icon: 'none',
              duration: 2000
            });
          }
        } else if (res.statusCode === 400) {
          // 参数错误
          this.setData({
            submitting: false
          });
          let errorMsg = '提交数据有误';
          if (res.data) {
            // 提取具体的错误信息
            if (typeof res.data === 'object') {
              const errors = [];
              for (let key in res.data) {
                if (Array.isArray(res.data[key])) {
                  errors.push(res.data[key].join(', '));
                } else {
                  errors.push(res.data[key]);
                }
              }
              errorMsg = errors.join('; ');
            } else {
              errorMsg = res.data;
            }
          }
          wx.showToast({
            title: errorMsg,
            icon: 'none',
            duration: 3000
          });
        } else if (res.statusCode === 401) {
          // 未授权
          this.setData({
            submitting: false
          });
          wx.showToast({
            title: '请重新登录',
            icon: 'none',
            success: () => {
              setTimeout(() => {
                wx.navigateTo({
                  url: '/pages/user/login/login'
                });
              }, 1500);
            }
          });
        } else {
          // 其他错误
          this.setData({
            submitting: false
          });
          wx.showToast({
            title: `提交失败: ${res.statusCode}`,
            icon: 'none',
            duration: 2000
          });
        }
      },
      fail: (err) => {
        wx.hideLoading();
        this.setData({
          submitting: false
        });
        console.error('请求失败:', err);
        wx.showToast({
          title: '网络错误，请检查网络连接',
          icon: 'none',
          duration: 2000
        });
      }
    });
  },

  /**
   * 表单验证
   */
  validateForm(formData) {
    // 验证联系人姓名
    if (!formData.contactName || formData.contactName.trim() === '') {
      return {
        valid: false,
        msg: '请输入联系人姓名'
      };
    }

    // 验证联系电话
    if (!formData.contactPhone || formData.contactPhone.length !== 11) {
      return {
        valid: false,
        msg: '请输入正确的11位手机号码'
      };
    }

    // 验证地区选择
    if (this.data.region.length === 0) {
      return {
        valid: false,
        msg: '请选择所在地区'
      };
    }

    // 验证车型
    if (!formData.carModel || formData.carModel.trim() === '') {
      return {
        valid: false,
        msg: '请输入车型信息'
      };
    }

    // 验证车辆照片
    if (!this.data.savedImagePath) {
      return {
        valid: false,
        msg: '请上传车辆照片'
      };
    }

    return {
      valid: true
    };
  },

  /**
   * 表单重置
   */
  formReset() {
    wx.showModal({
      title: '提示',
      content: '确定要重置表单吗？已填写的内容将被清空',
      success: (res) => {
        if (res.confirm) {
          // 重置所有数据
          this.setData({
            imageUrl: '',
            tempImagePath: '',
            savedImagePath: '',
            region: [],
            formData: {
              contactName: '',
              contactPhone: '',
              address: '',
              carModel: '',
              carCount: 1,
              wheelType: '',
              wheelCount: 0,
              ternaryCount: 0,
              batteryCount: 0,
              batteryPackCount: 0,
              engineCount: 0,
              weight: null,
              canStart: true,
              remark: ''
            }
          });

          wx.showToast({
            title: '表单已重置',
            icon: 'none',
            duration: 1500
          });
        }
      }
    });
  },

  /**
   * 页面卸载时保存草稿
   */
  onUnload() {
    // 可以在这里实现表单草稿保存功能
    console.log('页面卸载');
  }
});