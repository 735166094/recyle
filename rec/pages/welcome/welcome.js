import api from '../../config/settings'

Page({

  /**
   * 页面的初始数据
   */
  data: {
    second: 3,
    img: '/static/img/shuchangtu.jpg'
  },
  doJump() {
    //点击跳转
    wx.switchTab({
      url: '/pages/index/index',
    })
  },

  /**
   * 生命周期函数--监听页面加载
   */
  onLoad(options) {
    //向后端发送请求，获取广告图
    wx.request({
      url: api.welcome,
      method: 'GET',
      success: (res) => {
        if (res.data.code == 200) {
          this.setData({
            img: res.data.result
          })
        } else {
          wx.showToast({
            title: '网络请求异常',
          })
        }
      }
    })

    //启动定时器，倒计时
    var instance = setInterval(() => {
      if (this.data.second <= 0) {
        clearInterval(instance)
        wx.switchTab({
          url: '/pages/index/index',
        })
      } else {
        this.setData({
          second: this.data.second - 1
        })
      }

    }, 1000)
  },

  /**
   * 生命周期函数--监听页面初次渲染完成
   */
  onReady() {

  },

  /**
   * 生命周期函数--监听页面显示
   */
  onShow() {

  },

  /**
   * 生命周期函数--监听页面隐藏
   */
  onHide() {

  },

  /**
   * 生命周期函数--监听页面卸载
   */
  onUnload() {

  },

  /**
   * 页面相关事件处理函数--监听用户下拉动作
   */
  onPullDownRefresh() {

  },

  /**
   * 页面上拉触底事件的处理函数
   */
  onReachBottom() {

  },

  /**
   * 用户点击右上角分享
   */
  onShareAppMessage() {

  }
})