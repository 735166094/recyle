Page({
  data: {
    imageUrl: '', // 存储选中的图片路径
  },

  // 选择图片
  chooseImage() {
    const that = this;
    wx.chooseImage({
      count: 1, // 只允许选择1张图片
      sizeType: ['original', 'compressed'], // 可以指定是原图还是压缩图
      sourceType: ['album', 'camera'], // 可以指定来源是相册还是相机
      success(res) {
        // 返回选定照片的本地文件路径列表
        const tempFilePaths = res.tempFilePaths;
        that.setData({
          imageUrl: tempFilePaths[0]
        });
      }
    });
  },

  // 删除已选择的图片
  deleteImage() {
    this.setData({
      imageUrl: ''
    });
  },

  // 表单提交
  formSubmit(e) {
    const formData = e.detail.value;
    console.log('能否正常启动：', formData.canStart); 

    // 简单的表单验证
    if (!formData.contactName) {
      wx.showToast({
        title: '请输入联系人姓名',
        icon: 'none',
        duration: 2000
      });
      return;
    }

    if (!formData.contactPhone) {
      wx.showToast({
        title: '请输入联系电话',
        icon: 'none',
        duration: 2000
      });
      return;
    }

    // 验证电话号码格式
    const phoneReg = /^1[3-9]\d{9}$/;
    if (!phoneReg.test(formData.contactPhone)) {
      wx.showToast({
        title: '请输入正确的电话号码',
        icon: 'none',
        duration: 2000
      });
      return;
    }

    if (!formData.pickupAddress) {
      wx.showToast({
        title: '请输入取车地址',
        icon: 'none',
        duration: 2000
      });
      return;
    }

    if (!formData.carModel) {
      wx.showToast({
        title: '请输入车型',
        icon: 'none',
        duration: 2000
      });
      return;
    }

    if (!this.data.imageUrl) {
      wx.showToast({
        title: '请上传车辆照片',
        icon: 'none',
        duration: 2000
      });
      return;
    }

    // 添加图片信息到表单数据
    formData.imageUrl = this.data.imageUrl;

    // 这里可以添加提交到服务器的逻辑
    console.log('表单提交数据:', formData);

    // 模拟提交成功
    wx.showLoading({
      title: '提交中...',
    });

    setTimeout(() => {
      wx.hideLoading();
      wx.showToast({
        title: '提交成功',
        icon: 'success',
        duration: 2000
      });

      // 提交成功后重置表单
      this.setData({
        imageUrl: ''
      });

      // 可以在这里跳转到其他页面
      // setTimeout(() => {
      //   wx.navigateBack();
      // }, 2000);
    }, 1500);
  },

  // 表单重置
  formReset() {
    wx.showModal({
      title: '提示',
      content: '确定要重置表单吗？',
      success: (res) => {
        if (res.confirm) {
          this.setData({
            imageUrl: ''
          });
        }
      }
    });
  }
});