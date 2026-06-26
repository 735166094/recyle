const api = require('../../../config/settings')

Page({
  data: {
    tempImagePaths: [],
    isLoading: false,
    batchResult: null,
    errorMessage: '',
    showCamera: false,
    isBackCamera: true,
    supportCameraSwitch: false,
    isSwitchingCamera: false,
    cameraAuth: false,
    showPhotoPreview: false,
    currentPreviewImage: '',
    previewAfterCapture: true,
    isCapturing: false,
    cameraContext: null,

    // 证件类型配置
    certificateTypes: [],
    certificateTypeNames: [],
    selectedTypeIndex: 0,

    // 用户信息
    userInfo: null,
    isLoggedIn: false,

    // 上传进度
    uploadProgress: 0,
    currentUploadIndex: 0,

    // 添加状态存储标志
    shouldPersistType: true,

    // VIN码相关状态
    isSearchingVin: false,
    vinCode: '',
    vinResult: null,
    vinError: '',
    isClearingVin: false,

  },

  // 页面加载时初始化
  onLoad: function () {
    console.log('首页加载');
    this.checkLoginStatus();

    // 从本地存储读取之前选择的识别类型
    const savedTypeIndex = wx.getStorageSync('selectedTypeIndex');
    if (savedTypeIndex !== undefined && savedTypeIndex !== null) {
      this.setData({
        selectedTypeIndex: savedTypeIndex
      });
      console.log('恢复识别类型选择:', savedTypeIndex);
    }
    // 添加页面返回拦截
    // this.addPageBackInterceptor();
  },

  onShow: function () {
    console.log('首页显示');
    this.checkLoginStatus();

    // 读取预览设置
    const previewAfterCapture = wx.getStorageSync('previewAfterCapture');
    this.setData({
      previewAfterCapture: previewAfterCapture !== false
    });

    // 如果已登录，初始化其他功能
    if (this.data.isLoggedIn) {
      this.initCameraPermissions();
      this.fetchCertificateTypes();
    }
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
      this.setData({
        isLoggedIn: true,
        userInfo: employeeInfo
      });

      // 确保token同步到OCR系统
      if (!token) {
        wx.setStorageSync('token', employeeToken);
        console.log('同步员工token到OCR系统');
      }

      return true;
    }

    // 如果普通OCR系统已登录
    if (token && user) {
      console.log('使用OCR系统登录信息');
      this.setData({
        isLoggedIn: true,
        userInfo: user
      });
      return true;
    }

    // 未登录
    this.setData({
      isLoggedIn: false,
      userInfo: null
    });

    console.log('用户未登录，跳转到登录页');

    // 检查是否是从员工通道跳转过来的
    const appAccessToken = wx.getStorageSync('appAccessToken');
    const appUserInfo = wx.getStorageSync('appUserInfo');

    if (appAccessToken && appUserInfo) {
      console.log('检测到应用访问令牌，使用应用登录信息');

      // 使用应用访问信息登录
      wx.setStorageSync('token', appAccessToken);
      wx.setStorageSync('user', appUserInfo);

      this.setData({
        isLoggedIn: true,
        userInfo: appUserInfo
      });

      return true;
    }

    // 跳转到登录页
    this.redirectToLogin();
    return false;
  },

  // 跳转到登录页
  redirectToLogin: function () {
    const that = this;

    // 显示选择登录方式
    wx.showModal({
      title: '请选择登录方式',
      content: '您需要通过以下方式登录OCR系统',
      cancelText: '微信登录',
      confirmText: '员工登录',
      success: (res) => {
        if (res.confirm) {
          // 选择员工登录 - 跳转到员工通道
          wx.navigateTo({
            url: '/pages/user/employeepassage/employeepassage',
            success: () => {
              console.log('跳转到员工通道');
            }
          });
        } else {
          // 选择微信登录 - 跳转到普通登录页
          wx.redirectTo({
            url: '/pages/login/login?redirect=' + encodeURIComponent('/pages/ocr/index/index')
          });
        }
      },
      fail: (err) => {
        console.error('显示登录选项失败:', err);
        // 默认跳转到普通登录页
        wx.redirectTo({
          url: '/pages/login/login?redirect=' + encodeURIComponent('/pages/ocr/index/index')
        });
      }
    });
  },

  // 初始化相机权限
  initCameraPermissions: function () {
    this.checkCameraPermission();
    this.checkCameraSupport();
  },

  // 检查相机权限
  checkCameraPermission: function () {
    var that = this;
    wx.getSetting({
      success: function (res) {
        that.setData({
          cameraAuth: !!res.authSetting['scope.camera']
        });
      }
    });
  },

  // 检查设备是否支持摄像头切换
  checkCameraSupport: function () {
    try {
      const systemInfo = wx.getSystemInfoSync();
      const isMobile = systemInfo.platform === 'android' || systemInfo.platform === 'ios';
      const supportMultiCamera = isMobile &&
        (systemInfo.model.includes('iPhone') || ['HUAWEI', 'Xiaomi', 'OPPO', 'vivo', 'samsung'].some(function (brand) {
          return systemInfo.brand && systemInfo.brand.includes(brand);
        }));

      this.setData({
        supportCameraSwitch: supportMultiCamera
      });
    } catch (e) {
      console.error('获取设备信息失败:', e);
      this.setData({
        supportCameraSwitch: false
      });
    }
  },

  // 获取证件类型列表
  fetchCertificateTypes: function () {
    if (!this.data.isLoggedIn) {
      console.log('未登录，无法获取证件类型');
      return;
    }

    var that = this;

    // 获取所有可能的Token
    const employeeToken = wx.getStorageSync('employeeToken');
    const token = wx.getStorageSync('token');
    const appAccessToken = wx.getStorageSync('appAccessToken');

    console.log('Token检查:', {
      employeeToken: !!employeeToken,
      token: !!token,
      appAccessToken: !!appAccessToken
    });

    // 确定使用哪个Token
    let authToken = '';
    let tokenType = '';

    if (employeeToken) {
      authToken = employeeToken;
      tokenType = 'Bearer'; // 员工Token使用Bearer
      console.log('使用员工Token:', authToken.substring(0, 20) + '...');
    } else if (token) {
      authToken = token;
      tokenType = 'Token'; // 普通OCR Token使用Token
      console.log('使用OCR Token:', authToken.substring(0, 20) + '...');
    } else if (appAccessToken) {
      authToken = appAccessToken;
      tokenType = 'Bearer'; // 应用Token使用Bearer
      console.log('使用应用Token:', authToken.substring(0, 20) + '...');
    }

    if (!authToken) {
      console.error('没有可用的Token');
      that.setData({
        errorMessage: '登录状态异常，请重新登录'
      });
      wx.showToast({
        title: '请重新登录',
        icon: 'none'
      });
      return;
    }

    this.setData({
      isLoading: true,
      errorMessage: ''
    });

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
        console.log('获取证件类型响应状态码:', res.statusCode);
        console.log('获取证件类型完整响应:', res);

        if (res.statusCode === 200) {
          var certificateTypes = [];
          var rawData = res.data;

          //数据处理逻辑，直接使用返回的数组
          if (Array.isArray(rawData)) {
            certificateTypes = rawData;
          } else if (rawData && Array.isArray(rawData.results)) {
            certificateTypes = rawData.results;
          } else if (rawData && rawData.data && Array.isArray(rawData.data)) {
            certificateTypes = rawData.data;
          } else {
            // 如果都不是数组格式，尝试提取第一个数组属性
            for (var key in rawData) {
              if (Array.isArray(rawData[key])) {
                certificateTypes = rawData[key];
                break;
              }
            }
          }

          console.log('最终证件类型数据:', certificateTypes);

          if (certificateTypes.length === 0) {
            that.setData({
              errorMessage: '未找到可用的识别类型，请联系管理员'
            });
            wx.showToast({
              title: '无识别类型可用',
              icon: 'none'
            });
            return;
          }

          // 生成用于picker显示的纯名称数组
          var certificateTypeNames = certificateTypes.map(function (item) {
            return item.name || '未知类型';
          });
          console.log('证件类型名称数组:', certificateTypeNames);

          // 使用之前保存的选择，如果没有则使用默认选择逻辑
          var selectedIndex = wx.getStorageSync('selectedTypeIndex') || 0;

          // 确保索引在有效范围内
          if (selectedIndex >= certificateTypes.length) {
            selectedIndex = 0;
            wx.setStorageSync('selectedTypeIndex', 0);
          }

          // 如果没有保存的选择，使用默认逻辑
          if (selectedIndex === 0) {
            var autoIndex = certificateTypes.findIndex(function (item) {
              return item.type_code === 'auto_classification' ||
                (item.name && (item.name.includes('智能') || item.name.includes('自动')));
            });

            if (autoIndex !== -1) {
              selectedIndex = autoIndex;
              console.log('找到智能分类，索引:', selectedIndex);
            }
          }

          that.setData({
            certificateTypes: certificateTypes,
            certificateTypeNames: certificateTypeNames,
            selectedTypeIndex: selectedIndex
          });

          console.log('证件类型加载成功，数量:', certificateTypes.length);
          console.log('当前选择:', certificateTypes[selectedIndex] ? certificateTypes[selectedIndex].name : '未知');

        } else if (res.statusCode === 401) {
          console.error('认证失败，Token可能无效或过期');

          // 清除无效的Token
          wx.removeStorageSync('employeeToken');
          wx.removeStorageSync('token');
          wx.removeStorageSync('appAccessToken');
          wx.removeStorageSync('user');

          that.setData({
            isLoggedIn: false,
            userInfo: null,
            errorMessage: '登录已过期，请重新登录'
          });

          wx.showToast({
            title: '登录已过期',
            icon: 'none'
          });

          // 跳转到登录页
          setTimeout(function () {
            that.redirectToLogin();
          }, 1000);

        } else {
          var errorMsg = '请求失败: ' + res.statusCode;
          console.error(errorMsg);
          that.setData({
            errorMessage: errorMsg
          });
          wx.showToast({
            title: '获取识别类型失败',
            icon: 'none'
          });
        }
      },
      fail: function (err) {
        console.error('网络请求失败:', err);
        var errorMsg = '网络错误: ' + (err.errMsg || '未知错误');
        that.setData({
          errorMessage: errorMsg
        });
        wx.showToast({
          title: '网络请求失败',
          icon: 'none'
        });
      },
      complete: function () {
        that.setData({
          isLoading: false
        });
      }
    });
  },

  // 证件类型选择变化
  bindTypeChange: function (e) {
    var index = e.detail.value;
    console.log('用户选择的索引:', index);
    console.log('对应的证件类型:', this.data.certificateTypes[index]);

    // 保存到本地存储
    wx.setStorageSync('selectedTypeIndex', index);

    this.setData({
      selectedTypeIndex: index,
      shouldPersistType: true
    });

    var selectedType = this.data.certificateTypes[index];
    console.log('选择的识别类型：', selectedType.name, 'ID:', selectedType.id);
  },

  // 打开相机界面
  takePhoto: function () {
    if (!this.checkLoginStatus()) return;

    var that = this;

    // 检查相机权限
    wx.getSetting({
      success: function (res) {
        if (res.authSetting['scope.camera']) {
          that.openCamera();
        } else if (res.authSetting['scope.camera'] === undefined) {
          // 未请求过权限：首次申请
          wx.authorize({
            scope: 'scope.camera',
            success: function () {
              that.setData({
                cameraAuth: true
              });
              that.openCamera();
            },
            fail: function () {
              that.handleAuthDenied();
            }
          });
        } else {
          that.handleAuthDenied();
        }
      }
    });
  },

  // 打开相机
  openCamera: function () {
    this.setData({
      showCamera: true,
      batchResult: null,
      errorMessage: '',
      isCapturing: false
    });

    // 创建相机上下文
    this.setData({
      cameraContext: wx.createCameraContext()
    });
  },

  // 处理相机权限被拒绝的情况
  handleAuthDenied: function () {
    var that = this;
    wx.showModal({
      title: '权限不足',
      content: '需要相机权限才能使用拍照功能，请在设置中开启',
      confirmText: '去设置',
      cancelText: '取消',
      success: function (res) {
        if (res.confirm) {
          wx.openSetting();
        }
      }
    });
  },

  // 关闭相机界面
  closeCamera: function () {
    this.setData({
      showCamera: false,
      isCapturing: false,
      showPhotoPreview: false
    });
  },

  // 切换相机前后置
  switchCamera: function () {
    if (this.data.isSwitchingCamera || this.data.isCapturing) return;

    this.setData({
      isSwitchingCamera: true
    });

    var that = this;
    setTimeout(function () {
      that.setData({
        isBackCamera: !that.data.isBackCamera,
        isSwitchingCamera: false
      });
    }, 200);
  },

  // 拍摄照片
  capturePhoto: function () {
    if (this.data.isCapturing || this.data.isSwitchingCamera) {
      return;
    }

    var that = this;
    var previewAfterCapture = this.data.previewAfterCapture;
    var cameraContext = this.data.cameraContext;

    this.setData({
      isCapturing: true
    });

    wx.showToast({
      title: '拍照中...',
      icon: 'loading',
      duration: 2000,
      mask: true
    });

    cameraContext.takePhoto({
      quality: 'high',
      success: function (res) {
        var tempImagePath = res.tempImagePath;
        wx.hideToast();

        if (previewAfterCapture) {
          that.setData({
            showPhotoPreview: true,
            currentPreviewImage: tempImagePath,
            isCapturing: false
          });
        } else {
          // 直接添加到临时图片列表，不保存到相册
          that.addPhotoToTempList(tempImagePath);
        }
      },
      fail: function (err) {
        console.error('拍照失败:', err);
        wx.hideToast();
        wx.showToast({
          title: '拍照失败，请重试',
          icon: 'none'
        });
        that.setData({
          isCapturing: false
        });
      }
    });
  },

  // 保存照片（预览确认后）
  savePhoto: function () {
    var currentPreviewImage = this.data.currentPreviewImage;
    // 直接添加到临时图片列表，不保存到相册
    this.addPhotoToTempList(currentPreviewImage);
    this.setData({
      showPhotoPreview: false,
      currentPreviewImage: ''
    });
  },

  // 舍弃照片（预览确认后）
  discardPhoto: function () {
    this.setData({
      showPhotoPreview: false,
      currentPreviewImage: '',
      isCapturing: false
    });

    wx.showToast({
      title: '已舍弃照片',
      icon: 'none',
      duration: 1000
    });
  },

  // 添加照片到临时列表（不保存到相册）
  addPhotoToTempList: function (tempImagePath) {
    var tempImagePaths = this.data.tempImagePaths.concat([tempImagePath]);
    this.setData({
      tempImagePaths: tempImagePaths,
      isCapturing: false
    });

    wx.showToast({
      title: '照片已添加',
      icon: 'success',
      duration: 1000
    });
  },

  // 从相册选择图片
  chooseImage: function () {
    if (!this.checkLoginStatus()) return;

    var that = this;
    wx.chooseImage({
      count: 9,
      sizeType: ['original', 'compressed'],
      sourceType: ['album'],
      success: function (res) {
        var tempFilePaths = res.tempFilePaths;
        var newImages = that.data.tempImagePaths.concat(tempFilePaths);
        that.setData({
          tempImagePaths: newImages
        });

        wx.showToast({
          title: '已选择 ' + tempFilePaths.length + ' 张图片',
          icon: 'success',
          duration: 1500
        });
      },
      fail: function (err) {
        console.error('选择图片失败:', err);
        if (err.errMsg.includes('auth deny')) {
          wx.showModal({
            title: '权限不足',
            content: '需要相册权限才能选择图片，请在设置中开启',
            confirmText: '去设置',
            cancelText: '取消',
            success: function (res) {
              if (res.confirm) {
                wx.openSetting();
              }
            }
          });
        }
      }
    });
  },

  // 开始识别
  uploadImage: function () {
    if (!this.checkLoginStatus()) return;

    if (this.data.tempImagePaths.length === 0) {
      wx.showToast({
        title: '请先拍照或选择图片',
        icon: 'none',
        duration: 2000
      });
      return;
    }

    const token = wx.getStorageSync('token');

    // 确保有证件类型数据
    if (!this.data.certificateTypes || this.data.certificateTypes.length === 0) {
      wx.showToast({
        title: '识别类型加载中，请稍后重试',
        icon: 'none'
      });
      // 重新加载证件类型
      this.fetchCertificateTypes();
      return;
    }

    var selectedCertificateType = this.data.certificateTypes[this.data.selectedTypeIndex];
    if (!selectedCertificateType) {
      wx.showToast({
        title: '请先选择识别类型',
        icon: 'none'
      });
      return;
    }

    var certificateTypeId = selectedCertificateType.id;

    console.log('开始识别:', {
      typeName: selectedCertificateType.name,
      typeId: certificateTypeId,
      imageCount: this.data.tempImagePaths.length
    });

    this.setData({
      isLoading: true,
      errorMessage: '',
      batchResult: null,
      uploadProgress: 0,
      currentUploadIndex: 0
    });

    this.uploadBatchImages(token, certificateTypeId);
  },

  // 批量上传图片
  uploadBatchImages: function (token, certificateTypeId) {
    var that = this;
    var totalImages = this.data.tempImagePaths.length;

    // 使用对象来存储计数，这样可以通过引用传递
    var counts = {
      successCount: 0,
      failCount: 0
    };
    var failImagePaths = []; // 存储失败的图片路径
    var results = [];

    // 定义 uploadNext 函数，用于递归上传
    var uploadNext = function (index) {
      if (index >= totalImages) {
        // 所有图片上传完成
        that.setData({
          isLoading: false
        });

        // 设置批量结果
        that.setData({
          batchResult: {
            successCount: counts.successCount,
            failCount: counts.failCount,
            totalCount: totalImages,
            failImagePaths: failImagePaths
          }
        });

        var message = '处理完成 (' + counts.successCount + '成功/' + counts.failCount + '失败)';
        wx.showToast({
          title: message,
          icon: counts.successCount > 0 ? 'success' : 'none',
          duration: 2000
        });

        // 如果有失败的情况，显示详细错误
        if (counts.failCount > 0) {
          setTimeout(function () {
            wx.showModal({
              title: '处理结果',
              content: message,
              showCancel: false,
              confirmText: '知道了'
            });
          }, 2000);
        }

        return;
      }

      // 调用上传单张图片的函数
      that.uploadSingleImage(
        that.data.tempImagePaths[index],
        certificateTypeId,
        token,
        index,
        uploadNext,
        results,
        counts,
        failImagePaths
      );
    };

    uploadNext(0);
  },

  // 上传单张图片
  uploadSingleImage: function (filePath, certificateTypeId, token, index, nextCallback, results, counts, failImagePaths) {
    var that = this;
    var totalImages = this.data.tempImagePaths.length;

    // 先压缩图片
    wx.compressImage({
      src: filePath,
      quality: 80,
      success: function (compressRes) {
        // 上传压缩后的图片 - 修正参数顺序
        that.doUpload(
          compressRes.tempFilePath, // 参数1: filePath
          certificateTypeId, // 参数2: certificateTypeId
          token, // 参数3: token
          index, // 参数4: index
          nextCallback, // 参数5: nextCallback
          results, // 参数6: results
          counts, // 参数7: counts
          failImagePaths, // 参数8: failImagePaths
          totalImages // 参数9: totalImages
        );
      },
      fail: function (err) {
        console.error('图片压缩失败', err);
        // 压缩失败也尝试上传原图片
        that.doUpload(
          filePath, // 参数1: filePath
          certificateTypeId, // 参数2: certificateTypeId
          token, // 参数3: token
          index, // 参数4: index
          nextCallback, // 参数5: nextCallback
          results, // 参数6: results
          counts, // 参数7: counts
          failImagePaths, // 参数8: failImagePaths
          totalImages // 参数9: totalImages
        );
      }
    });
  },

  // 执行上传
  doUpload: function (filePath, certificateTypeId, token, index, nextCallback, results, counts, failImagePaths, totalImages) {
    var that = this;

    // 获取所有可能的Token
    const employeeToken = wx.getStorageSync('employeeToken');
    const ocrToken = wx.getStorageSync('token');
    const appAccessToken = wx.getStorageSync('appAccessToken');

    // 确定使用哪个Token
    let authToken = '';
    let tokenType = '';

    // 重要：如果参数中有token，优先使用参数中的token
    if (token) {
      authToken = token;
      // 判断token类型
      if (token.startsWith('ey') && token.includes('.') && token.split('.').length === 3) {
        // JWT token格式，使用Bearer
        tokenType = 'Bearer';
      } else {
        tokenType = 'Token';
      }
    } else if (employeeToken) {
      authToken = employeeToken;
      tokenType = 'Bearer';
    } else if (appAccessToken) {
      authToken = appAccessToken;
      tokenType = 'Bearer';
    } else if (ocrToken) {
      authToken = ocrToken;
      tokenType = 'Token';
    }

    if (!authToken) {
      console.error('没有可用的Token');

      // 确保results是数组
      if (!Array.isArray(results)) {
        console.error('results不是数组，重新初始化');
        results = [];
      }

      results.push({
        index: index,
        success: false,
        error: '登录状态异常'
      });
      counts.failCount++;
      failImagePaths.push(that.data.tempImagePaths[index]);

      that.setData({
        errorMessage: '登录状态异常，请重新登录'
      });

      nextCallback(index + 1);
      return;
    }

    // 构建请求头
    const headers = {
      'Authorization': `${tokenType} ${authToken}`
    };

    wx.uploadFile({
      url: api.upload,
      filePath: filePath,
      name: 'image',
      header: headers,
      formData: {
        'certificate_type_id': certificateTypeId || ''
      },
      timeout: 60000,
      success: function (res) {
        try {
          var data = JSON.parse(res.data);

          // 确保results是数组
          if (!Array.isArray(results)) {
            console.error('success回调中results不是数组，重新初始化');
            results = [];
          }

          if (res.statusCode === 201) {
            // 上传成功
            results.push({
              index: index,
              success: true,
              data: data
            });
            counts.successCount++;

            wx.showToast({
              title: '第' + (index + 1) + '张识别成功',
              icon: 'success',
              duration: 1500
            });

          } else if (res.statusCode === 401) {
            // Token过期或无效
            console.error('Token无效或已过期');
            results.push({
              index: index,
              success: false,
              error: '登录已过期，请重新登录'
            });
            counts.failCount++;
            failImagePaths.push(that.data.tempImagePaths[index]);

            // 清除无效的Token
            wx.removeStorageSync('employeeToken');
            wx.removeStorageSync('token');
            wx.removeStorageSync('appAccessToken');
            wx.removeStorageSync('user');

            that.setData({
              isLoggedIn: false,
              userInfo: null,
              errorMessage: '登录已过期，请重新登录'
            });

            wx.showToast({
              title: '登录已过期',
              icon: 'none',
              duration: 1500
            });

          } else {
            results.push({
              index: index,
              success: false,
              error: data.error || '识别失败'
            });
            counts.failCount++;
            failImagePaths.push(that.data.tempImagePaths[index]);

            that.setData({
              errorMessage: data.error || '第' + (index + 1) + '张图片识别失败'
            });

            wx.showToast({
              title: '第' + (index + 1) + '张识别失败',
              icon: 'none',
              duration: 1500
            });
          }
        } catch (e) {
          console.error('解析响应失败:', e);

          // 确保results是数组
          if (!Array.isArray(results)) {
            console.error('catch中results不是数组，重新初始化');
            results = [];
          }

          results.push({
            index: index,
            success: false,
            error: '数据解析错误'
          });
          counts.failCount++;
          failImagePaths.push(that.data.tempImagePaths[index]);
        }

        // 更新进度
        that.setData({
          uploadProgress: Math.floor(((index + 1) / totalImages) * 100),
          currentUploadIndex: index + 1
        });

        nextCallback(index + 1);
      },
      fail: function (err) {
        console.error('上传失败:', err);

        // 确保results是数组
        if (!Array.isArray(results)) {
          console.error('fail回调中results不是数组，重新初始化');
          results = [];
        }

        results.push({
          index: index,
          success: false,
          error: '上传失败'
        });
        counts.failCount++;
        failImagePaths.push(that.data.tempImagePaths[index]);

        that.setData({
          errorMessage: '第' + (index + 1) + '张图片上传失败'
        });

        nextCallback(index + 1);
      }
    });
  },

  // 预览大图
  previewFullImage: function (e) {
    var index = e.currentTarget.dataset.index;
    var tempImagePaths = this.data.tempImagePaths;

    wx.previewImage({
      current: tempImagePaths[index],
      urls: tempImagePaths
    });
  },

  // 删除单张图片
  deleteImage: function (e) {
    var that = this;
    var index = e.currentTarget.dataset.index;
    var tempImagePaths = this.data.tempImagePaths;

    wx.showModal({
      title: '提示',
      content: '确定要删除这张照片吗？',
      confirmText: '删除',
      cancelText: '取消',
      success: function (res) {
        if (res.confirm) {
          tempImagePaths.splice(index, 1);
          that.setData({
            tempImagePaths: tempImagePaths
          });

          wx.showToast({
            title: '删除成功',
            icon: 'success',
            duration: 1000
          });
        }
      }
    });
  },

  // 清空所有图片
  clearAllImages: function () {
    var that = this;
    wx.showModal({
      title: '提示',
      content: '确定要清空所有照片吗？',
      confirmText: '清空',
      cancelText: '取消',
      success: function (res) {
        if (res.confirm) {
          that.setData({
            tempImagePaths: [],
            batchResult: null
          });

          wx.showToast({
            title: '已清空所有图片',
            icon: 'success',
            duration: 1000
          });
        }
      }
    });
  },

  // 重新选择方法
  rechooseImage: function () {
    var that = this;
    if (this.data.tempImagePaths.length > 0) {
      wx.showModal({
        title: '提示',
        content: '重新拍摄将清空现有照片，是否继续？',
        confirmText: '继续',
        cancelText: '取消',
        success: function (res) {
          if (res.confirm) {
            that.setData({
              tempImagePaths: [],
              batchResult: null
            });
            that.takePhoto();
          }
        }
      });
    } else {
      this.takePhoto();
    }
  },


  // 返回employeepassage页面
  goToBack: function () {
    wx.navigateTo({
      url: '/pages/user/employeepassage/employeepassage'
    });
  },

  // 跳转奇奇回收首页
  goToHome: function () {
    wx.switchTab({
      url: '/pages/index/index'
    });
  },


  // 跳转到设置页面
  goToSetting: function () {
    if (!this.checkLoginStatus()) return;

    wx.navigateTo({
      url: '/pages/ocr/settings/settings/settings'
    });
  },


  // 跳转到历史页面
  goToHistory: function () {
    if (!this.checkLoginStatus()) return;

    wx.navigateTo({
      url: '/pages/ocr/history/histories/histories'
    });
  },

  // 相机错误处理
  cameraError: function (e) {
    console.error('相机错误:', e.detail);
    wx.showToast({
      title: '相机发生错误',
      icon: 'none'
    });
    this.closeCamera();
  },

  // 显示用户信息
  showUserInfo: function () {
    if (this.data.userInfo) {
      var user = this.data.userInfo;
      wx.showModal({
        title: '用户信息',
        content: '用户名：' + user.username + '\n邮箱：' + (user.email || '未设置'),
        showCancel: false,
        confirmText: '知道了'
      });
    }
  },

  // VIN码输入处理
  onVinInput: function (e) {
    this.setData({
      vinCode: e.detail.value
    });
  },

  // 处理VIN码搜索确认（回车键）
  handleVinSearch: function () {
    this.searchVin();
  },




  // 帮助函数
  getAuthHeader: function () {
    // 优先使用员工token，如果不存在则使用普通token
    const employeeToken = wx.getStorageSync('employeeToken');
    const token = wx.getStorageSync('token');
    const appAccessToken = wx.getStorageSync('appAccessToken');

    // 确定使用哪个token和token类型
    let authToken = '';
    let tokenType = '';

    if (employeeToken) {
      authToken = employeeToken;
      tokenType = 'Bearer';
    } else if (appAccessToken) {
      authToken = appAccessToken;
      tokenType = 'Bearer';
    } else if (token) {
      authToken = token;
      tokenType = 'Token';
    }

    if (!authToken) {
      console.error('没有可用的Token');
      return null;
    }

    return {
      'Authorization': tokenType + ' ' + authToken,
      'Content-Type': 'application/json'
    };
  },

  // searchVin 
  searchVin: function () {
    var vinCode = this.data.vinCode.trim();

    // 验证VIN码长度
    if (vinCode.length !== 17) {
      wx.showToast({
        title: 'VIN码应为17位字符',
        icon: 'none'
      });
      return;
    }

    if (!this.checkLoginStatus()) return;

    // 获取认证头
    const headers = this.getAuthHeader();
    if (!headers) {
      wx.showToast({
        title: '请先登录',
        icon: 'none'
      });
      return;
    }

    this.setData({
      isSearchingVin: true,
      vinResult: null,
      vinError: ''
    });

    var that = this;
    wx.request({
      url: api.vinSearch,
      method: 'POST',
      header: headers,
      data: {
        vin: vinCode
      },
      success: function (res) {
        console.log('VIN查询响应:', res);

        if (res.statusCode === 200) {
          // 成功
          var result = res.data;
          that.setData({
            vinResult: result
          });
          wx.showToast({
            title: '查询成功',
            icon: 'success'
          });
        } else if (res.statusCode === 401) {
          // 未授权
          that.setData({
            vinError: '登录已过期，请重新登录'
          });
          wx.showToast({
            title: '请重新登录',
            icon: 'none'
          });

          // 清除token，跳转到登录
          wx.removeStorageSync('employeeToken');
          wx.removeStorageSync('token');
          wx.removeStorageSync('user');
          setTimeout(() => {
            that.redirectToLogin();
          }, 1000);
        } else if (res.statusCode === 403) {
          // 权限不足
          that.setData({
            vinError: '您没有权限进行VIN查询'
          });
          wx.showToast({
            title: '权限不足',
            icon: 'none'
          });
        } else {
          // 其他错误
          var errorMsg = res.data.message || '查询失败';
          that.setData({
            vinError: errorMsg
          });
          wx.showToast({
            title: '查询失败',
            icon: 'none'
          });
        }
      },
      fail: function (err) {
        console.error('VIN码查询失败:', err);
        that.setData({
          vinError: '网络错误，请重试'
        });
        wx.showToast({
          title: '网络错误',
          icon: 'none'
        });
      },
      complete: function () {
        that.setData({
          isSearchingVin: false
        });
      }
    });
  },


  // 复制单个车型信息
  copyModelInfo: function (e) {
    var modelIndex = e.currentTarget.dataset.modelindex;
    var model = this.data.vinResult.models[modelIndex];

    if (!model) {
      wx.showToast({
        title: '没有可复制的数据',
        icon: 'none'
      });
      return;
    }

    var copyText = this.formatModelInfoForCopy(model);

    wx.setClipboardData({
      data: copyText,
      success: function () {
        wx.showToast({
          title: '车型信息已复制',
          icon: 'success'
        });
      },
      fail: function (err) {
        console.error('复制失败:', err);
        wx.showToast({
          title: '复制失败',
          icon: 'none'
        });
      }
    });
  },

  // 格式化单个车型信息用于复制
  formatModelInfoForCopy: function (model) {
    var lines = [];
    if (model.model_detail) lines.push('车型: ' + model.model_detail);
    if (model.factory) lines.push('厂家: ' + model.factory);
    if (model.series) lines.push('车系: ' + model.series);
    if (model.sales_version) lines.push('销售版本: ' + model.sales_version);
    if (model.cc) lines.push('排量: ' + model.cc + 'cc');
    if (model.engine_no) lines.push('发动机: ' + model.engine_no);
    if (model.price) lines.push('参考价格: ' + model.price + '元');
    return lines.join('\n');
  },

  // 复制VIN查询结果
  copyVinResult: function () {
    if (!this.data.vinResult || !this.data.vinResult.success) {
      wx.showToast({
        title: '没有可复制的数据',
        icon: 'none'
      });
      return;
    }

    var that = this;
    var result = this.data.vinResult;
    var copyText = this.formatVinResultForCopy(result);

    wx.setClipboardData({
      data: copyText,
      success: function () {
        wx.showToast({
          title: '结果已复制',
          icon: 'success'
        });
      },
      fail: function (err) {
        console.error('复制失败:', err);
        wx.showToast({
          title: '复制失败',
          icon: 'none'
        });
      }
    });
  },

  // 格式化VIN查询结果用于复制
  formatVinResultForCopy: function (result) {
    var lines = [];
    lines.push('=== VIN码查询结果 ===');
    lines.push('VIN码: ' + (result.vin_code || ''));
    lines.push('查询状态: 成功');
    lines.push('处理时间: ' + (result.processing_time || '0') + '秒');

    // 基本信息
    if (result.basic_info) {
      lines.push('');
      lines.push('【基本信息】');
      if (result.basic_info.brand) lines.push('品牌: ' + result.basic_info.brand);
      if (result.basic_info.model_year) lines.push('生产年份: ' + result.basic_info.model_year);
      if (result.basic_info.build_date) lines.push('生产日期: ' + result.basic_info.build_date);
      if (result.basic_info.epc_cn) lines.push('品牌中文: ' + result.basic_info.epc_cn);
    }

    // 车型信息
    if (result.models && result.models.length > 0) {
      lines.push('');
      lines.push('【车型信息】');
      result.models.forEach(function (model, index) {
        lines.push('车型 ' + (index + 1) + ':');
        if (model.model_detail) lines.push('  车型: ' + model.model_detail);
        if (model.factory) lines.push('  厂家: ' + model.factory);
        if (model.series) lines.push('  车系: ' + model.series);
        if (model.sales_version) lines.push('  销售版本: ' + model.sales_version);
        if (model.cc) lines.push('  排量: ' + model.cc + 'cc');
        if (model.engine_no) lines.push('  发动机: ' + model.engine_no);
        if (model.price) lines.push('  参考价格: ' + model.price + '元');
      });
    }

    // 主要属性
    if (result.main_attributes && result.main_attributes.length > 0) {
      lines.push('');
      lines.push('【主要属性】');
      result.main_attributes.forEach(function (attr) {
        if (attr.name && attr.value) {
          lines.push(attr.name + ': ' + attr.value);
        }
      });
    }

    lines.push('');
    lines.push('=== 查询结束 ===');

    return lines.join('\n');
  },

  // 清空VIN码查询结果
  clearVinResult: function () {
    this.setData({
      vinCode: '',
      vinResult: null,
      vinError: ''
    });
  },

  // 复制文本到剪贴板
  copyToClipboard: function (e) {
    const text = e.currentTarget.dataset.text;
    if (!text) {
      wx.showToast({
        title: '没有可复制的数据',
        icon: 'none'
      });
      return;
    }

    wx.setClipboardData({
      data: text,
      success: () => {
        wx.showToast({
          title: '复制成功',
          icon: 'success'
        });
      },
      fail: (err) => {
        console.error('复制失败:', err);
        wx.showToast({
          title: '复制失败',
          icon: 'none'
        });
      }
    });
  },


});