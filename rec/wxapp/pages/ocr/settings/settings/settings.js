// pages/ocr/settings/settings.js
const app = getApp();

Page({
  data: {
    previewAfterCapture: true,
    cacheSize: '计算中...',
    version: '1.0.0',
    showClearCacheModal: false,
    showProgressModal: false,
    clearProgress: 0,
    clearStatus: '正在准备清除...'
  },

  onLoad() {
    this.loadSettings();
    this.calculateCacheSize();
    this.getAppVersion();
  },

  onShow() {
    // 重新计算缓存大小
    this.calculateCacheSize();
  },

  // 加载设置
  loadSettings() {
    const previewAfterCapture = wx.getStorageSync('previewAfterCapture');
    
    this.setData({
      previewAfterCapture: previewAfterCapture !== false
    });
  },

  // 拍照预览设置变化
  onPreviewSettingChange(e) {
    const checked = e.detail.value;
    this.setData({
      previewAfterCapture: checked
    });

    wx.setStorageSync('previewAfterCapture', checked);

    wx.showToast({
      title: checked ? '已开启预览确认' : '已关闭预览确认',
      icon: 'none',
      duration: 1500
    });
  },

  // 计算缓存大小
  calculateCacheSize() {
    const that = this;
    wx.getStorageInfo({
      success: function(res) {
        const sizeKB = res.currentSize;
        let displaySize;
        
        if (sizeKB < 1024) {
          displaySize = sizeKB + ' KB';
        } else {
          displaySize = (sizeKB / 1024).toFixed(2) + ' MB';
        }
        
        that.setData({
          cacheSize: displaySize
        });
      },
      fail: function() {
        that.setData({
          cacheSize: '未知'
        });
      }
    });
  },

  // 获取应用版本
  getAppVersion() {
    const accountInfo = wx.getAccountInfoSync();
    if (accountInfo && accountInfo.miniProgram) {
      this.setData({
        version: accountInfo.miniProgram.version || '1.0.0'
      });
    }
  },

  // 显示清除缓存弹窗
  showClearCacheModal() {
    this.setData({
      showClearCacheModal: true
    });
  },

  // 隐藏清除缓存弹窗
  hideClearCacheModal() {
    this.setData({
      showClearCacheModal: false
    });
  },

  // 确认清除缓存
  confirmClearCache() {
    this.setData({
      showClearCacheModal: false,
      showProgressModal: true,
      clearProgress: 0,
      clearStatus: '正在准备清除...'
    });

    this.startClearCache();
  },

  // 开始清除缓存
  startClearCache() {
    const that = this;
    
    // 步骤1：备份重要数据
    that.updateProgress(10, '备份重要数据...');
    
    const importantData = {
      token: wx.getStorageSync('token'),
      user: wx.getStorageSync('user'),
      previewAfterCapture: that.data.previewAfterCapture
    };

    setTimeout(() => {
      // 步骤2：清除识别历史记录
      that.updateProgress(30, '清除识别历史记录...');
      that.clearRecognitionHistory();
    }, 500);

    setTimeout(() => {
      // 步骤3：清除临时文件
      that.updateProgress(50, '清除临时图片文件...');
      that.clearTempFiles();
    }, 1000);

    setTimeout(() => {
      // 步骤4：清除本地存储
      that.updateProgress(70, '清除本地存储数据...');
      that.clearStorageData(importantData);
    }, 1500);

    setTimeout(() => {
      // 步骤5：完成
      that.updateProgress(100, '清除完成');
      
      setTimeout(() => {
        that.setData({
          showProgressModal: false,
          cacheSize: '0 KB'
        });

        wx.showToast({
          title: '缓存清除成功',
          icon: 'success',
          duration: 2000
        });

        // 重新计算缓存大小
        setTimeout(() => {
          that.calculateCacheSize();
        }, 1000);
      }, 500);
    }, 2000);
  },

  // 更新进度
  updateProgress(progress, status) {
    this.setData({
      clearProgress: progress,
      clearStatus: status
    });
  },

  // 清除识别历史记录
  clearRecognitionHistory() {
    try {
      // 清除本地存储的识别记录
      const historyKeys = [
        'recognition_history',
        'ocr_records',
        'recent_records',
        'batch_records'
      ];
      
      historyKeys.forEach(key => {
        wx.removeStorageSync(key);
      });
      
      // 通知历史页面刷新
      this.notifyHistoryPageRefresh();
    } catch (error) {
      console.error('清除识别历史记录失败:', error);
    }
  },

  // 通知历史页面刷新
  notifyHistoryPageRefresh() {
    // 获取当前页面栈
    const pages = getCurrentPages();
    pages.forEach(page => {
      if (page.route === 'pages/ocr/history/histories/histories') {
        // 如果历史页面存在，调用其刷新方法
        if (page.refreshData) {
          page.refreshData();
        }
      }
    });
  },

  // 清除临时文件
  clearTempFiles() {
    return new Promise((resolve) => {
      // 获取文件系统管理器
      const fs = wx.getFileSystemManager();
      
      try {
        // 尝试清除微信临时目录
        const tempDir = `${wx.env.USER_DATA_PATH}/temp`;
        
        // 注意：小程序无法直接删除目录，这里主要清除的是存储的临时文件路径引用
        // 实际的临时文件由微信自动管理
        
        // 清除图片预览缓存
        const tempImageKeys = [
          'temp_image_paths',
          'camera_temp_files',
          'selected_images'
        ];
        
        tempImageKeys.forEach(key => {
          wx.removeStorageSync(key);
        });
        
        resolve();
      } catch (error) {
        console.error('清除临时文件失败:', error);
        resolve();
      }
    });
  },

  // 清除存储数据（保留重要数据）
  clearStorageData(importantData) {
    return new Promise((resolve) => {
      try {
        // 获取所有存储的key
        wx.getStorageInfo({
          success: (res) => {
            const keys = res.keys;
            let clearedCount = 0;
            const totalKeys = keys.length;

            keys.forEach(key => {
              // 保留重要数据
              if (!['token', 'user', 'previewAfterCapture'].includes(key)) {
                wx.removeStorageSync(key);
              }
              clearedCount++;
              
              // 更新进度
              const progress = 70 + Math.floor((clearedCount / totalKeys) * 20);
              this.updateProgress(progress, `清除本地数据 (${clearedCount}/${totalKeys})`);
            });

            // 重新设置重要数据
            if (importantData.token) {
              wx.setStorageSync('token', importantData.token);
            }
            if (importantData.user) {
              wx.setStorageSync('user', importantData.user);
            }
            wx.setStorageSync('previewAfterCapture', importantData.previewAfterCapture);

            // 更新全局数据
            if (app.globalData) {
              app.globalData.token = importantData.token;
              app.globalData.userInfo = importantData.user;
              app.globalData.hasLogin = !!importantData.token;
            }

            resolve();
          },
          fail: () => {
            resolve();
          }
        });
      } catch (error) {
        console.error('清除存储数据失败:', error);
        resolve();
      }
    });
  },

  // 跳转到用户协议
  navigateToAgreement() {
    wx.navigateTo({
      url: '/pages/ocr/settings/agreement/agreement?type=agreement'
    });
  },

  // 跳转到隐私政策
  navigateToPrivacy() {
    wx.navigateTo({
      url: '/pages/ocr/settings/agreement/agreement?type=privacy'
    });
  },

  // 跳转到关于我们
  navigateToAbout() {
    wx.navigateTo({
      url: '/pages/user/aboutour/aboutour'
    });
  },

  // 检查更新
  checkUpdate() {
    const updateManager = wx.getUpdateManager();

    updateManager.onCheckForUpdate(function(res) {
      console.log('是否有新版本：', res.hasUpdate);
    });

    updateManager.onUpdateReady(function() {
      wx.showModal({
        title: '更新提示',
        content: '新版本已准备好，是否重启应用？',
        success: function(res) {
          if (res.confirm) {
            updateManager.applyUpdate();
          }
        }
      });
    });

    updateManager.onUpdateFailed(function() {
      wx.showToast({
        title: '更新失败',
        icon: 'none'
      });
    });
  }
});