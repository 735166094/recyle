// utils/utils.js
const app = getApp()
const settings = require('../config/settings.js')

const formatTime = date => {
  const year = date.getFullYear()
  const month = date.getMonth() + 1
  const day = date.getDate()
  const hour = date.getHours()
  const minute = date.getMinutes()
  const second = date.getSeconds()

  return `${[year, month, day].map(formatNumber).join('/')} ${[hour, minute, second].map(formatNumber).join(':')}`
}

const formatNumber = n => {
  n = n.toString()
  return n[1] ? n : `0${n}`
}

const request = (url, options) => {
  return new Promise((resolve, reject) => {
    const token = wx.getStorageSync('token')

    // 确保URL是完整的 - 使用settings中的baseUrl
    let fullUrl = url
    if (!url.startsWith('http')) {
      fullUrl = settings.baseUrl + (url.startsWith('/') ? url : '/' + url)
    }

    wx.request({
      url: fullUrl,
      method: options.method || 'GET',
      data: options.data || {},
      header: {
        'Content-Type': 'application/json',
        'Authorization': token ? `Bearer ${token}` : '',
        ...options.header
      },
      success(res) {
        if (res.statusCode === 200) {
          resolve(res.data)
        } else {
          reject({
            status: res.statusCode,
            message: res.data && res.data.detail ? res.data.detail : '请求失败',
            data: res.data
          })
        }
      },
      fail(err) {
        reject({
          status: 0,
          message: '网络请求失败',
          error: err
        })
      }
    })
  })
}

// GET请求
const get = (url, options = {}) => {
  return request(url, {
    ...options,
    method: 'GET'
  })
}

// POST请求  
const post = (url, options = {}) => {
  return request(url, {
    ...options,
    method: 'POST'
  })
}

// PUT请求
const put = (url, options = {}) => {
  return request(url, {
    ...options,
    method: 'PUT'
  })
}

// DELETE请求
const del = (url, options = {}) => {
  return request(url, {
    ...options,
    method: 'DELETE'
  })
}

// 上传文件
const uploadFile = (url, filePath, formData = {}, options = {}) => {
  return new Promise((resolve, reject) => {
    const token = wx.getStorageSync('token')
    let fullUrl = url
    if (!url.startsWith('http')) {
      fullUrl = settings.baseUrl + (url.startsWith('/') ? url : '/' + url)
    }

    wx.uploadFile({
      url: fullUrl,
      filePath: filePath,
      name: options.name || 'file',
      formData: formData,
      header: {
        'Authorization': token ? `Bearer ${token}` : '',
        ...options.header
      },
      success(res) {
        if (res.statusCode === 200) {
          try {
            const data = JSON.parse(res.data)
            resolve(data)
          } catch (e) {
            resolve(res.data)
          }
        } else {
          reject({
            status: res.statusCode,
            message: '文件上传失败',
            data: res.data
          })
        }
      },
      fail(err) {
        reject({
          status: 0,
          message: '文件上传失败',
          error: err
        })
      }
    })
  })
}

// 检查登录状态
const checkLogin = () => {
  const token = wx.getStorageSync('token')
  if (!token) {
    wx.showModal({
      title: '提示',
      content: '请先登录',
      success(res) {
        if (res.confirm) {
          wx.navigateTo({
            url: '/pages/user/login/login'
          })
        }
      }
    })
    return false
  }
  return true
}

// 处理API响应
const handleApiResponse = (res, successCallback, errorCallback) => {
  if (res && (res.success || res.results !== undefined)) {
    successCallback && successCallback(res)
  } else {
    const errorMsg = res.message || '请求失败'
    errorCallback && errorCallback(errorMsg)
    wx.showToast({
      title: errorMsg,
      icon: 'none',
      duration: 2000
    })
  }
}

// 获取完整图片URL - 使用settings配置
const getFullImageUrl = (imagePath) => {
  if (!imagePath) return '/images/default-car.png'

  // 如果已经是完整URL，直接返回
  if (imagePath.startsWith('http://') || imagePath.startsWith('https://')) {
    return imagePath
  }

  // 使用settings中的serverBaseUrl
  return `${settings.serverBaseUrl}${imagePath.startsWith('/') ? '' : '/'}${imagePath}`
}

// 格式化日期时间
const formatDateTime = (dateTimeStr) => {
  if (!dateTimeStr) return ''

  try {
    const date = new Date(dateTimeStr)
    return `${date.getFullYear()}-${(date.getMonth() + 1).toString().padStart(2, '0')}-${date.getDate().toString().padStart(2, '0')} ${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`
  } catch (e) {
    return dateTimeStr
  }
}

// 获取显示价格 - 当最终价格为空时显示预估价格
const getDisplayPrice = (item) => {
  if (item.final_price !== null && item.final_price !== undefined) {
    return item.final_price
  } else if (item.estimated_price !== null && item.estimated_price !== undefined) {
    return item.estimated_price
  }
  return null
}

// 格式化价格显示
const formatPrice = (price) => {
  if (price === null || price === undefined) return '待评估'
  return `¥${parseFloat(price).toFixed(2)}`
}

module.exports = {
  formatTime,
  formatNumber,
  request,
  get,
  post,
  put,
  del,
  uploadFile,
  checkLogin,
  handleApiResponse,
  getFullImageUrl,
  formatDateTime,
  getDisplayPrice,
  formatPrice,
  settings
}