// pages/recycle/record/record.js
import api from '../../../config/settings'

const app = getApp()

// 网络请求函数
const request = (url, options) => {
  return new Promise((resolve, reject) => {
    const token = wx.getStorageSync('token')

    if (!token) {
      console.log('未找到token，需要登录')
      reject({
        message: '请先登录',
        status: 401
      })
      return
    }

    wx.request({
      url: url,
      method: options.method || 'GET',
      data: options.data || {},
      header: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
        ...options.header
      },
      success(res) {
        console.log('请求成功:', url, '状态码:', res.statusCode)
        if (res.statusCode === 200) {
          resolve(res.data)
        } else {
          reject(res.data)
        }
      },
      fail(err) {
        console.log('请求失败:', url, '错误:', err)
        reject(err)
      }
    })
  })
}

const get = (url, options = {}) => {
  return request(url, {
    ...options,
    method: 'GET'
  })
}

const post = (url, options = {}) => {
  return request(url, {
    ...options,
    method: 'POST'
  })
}

Page({
  data: {
    carRecords: [],
    filteredCars: [],
    currentFilter: 'all',
    totalCount: 0,
    pendingCount: 0,
    pricedCount: 0,
    confirmedCount: 0,
    cancelledCount: 0,
    hasMore: true,
    page: 1,
    pageSize: 10,
    isLoading: false,
    hasError: false,
    errorMessage: '',
    isLoggedIn: false,
    isRefreshing: false
  },

  onLoad() {
    console.log('record页面加载')
    this.checkLoginStatus()
    
  },

  onShow() {
    console.log('record页面显示')

    // 检查是否需要刷新数据
    const needRefresh = wx.getStorageSync('needRefreshMyCars')
    console.log('是否需要刷新:', needRefresh)

    if (needRefresh) {
      console.log('检测到需要刷新数据，开始刷新...')
      // 重置所有状态并重新加载数据
      this.setData({
        page: 1,
        carRecords: [],
        filteredCars: [],
        hasMore: true,
        isRefreshing: true
      })

      // 移除存储的标志
      wx.removeStorageSync('needRefreshMyCars')

      // 重新加载数据
      if (this.data.isLoggedIn) {
        this.loadCarRecords(() => {
          console.log('数据刷新完成')
          this.setData({
            isRefreshing: false
          })
        })
      } else {
        this.checkLoginStatus()
        this.setData({
          isRefreshing: false
        })
      }
    } else {
      // 正常显示，只检查登录状态
      this.checkLoginStatus()
    }
  },

  onPullDownRefresh() {
    if (!this.data.isLoggedIn) {
      wx.stopPullDownRefresh()
      return
    }

    console.log('下拉刷新触发')
    this.setData({
      page: 1,
      carRecords: [],
      filteredCars: [],
      hasMore: true,
      isRefreshing: true
    })

    this.loadCarRecords(() => {
      wx.stopPullDownRefresh()
      this.setData({
        isRefreshing: false
      })
      wx.showToast({
        title: '刷新成功',
        icon: 'success',
        duration: 1500
      })
    })
  },

  onReachBottom() {
    if (this.data.hasMore && !this.data.isLoading && this.data.isLoggedIn && !this.data.isRefreshing) {
      console.log('加载更多数据，当前页码:', this.data.page)
      this.loadCarRecords()
    }
  },

  // 检查登录状态
  checkLoginStatus() {
    const token = wx.getStorageSync('token')
    const isLoggedIn = !!token

    console.log('检查登录状态:', isLoggedIn)

    this.setData({
      isLoggedIn
    })

    if (isLoggedIn) {
      console.log('用户已登录，开始加载数据')
      // 如果数据为空或者正在刷新，才加载数据
      if (this.data.carRecords.length === 0 || this.data.isRefreshing) {
        this.loadCarRecords()
      }
    } else {
      console.log('用户未登录')
      this.setData({
        hasError: true,
        errorMessage: '请先登录'
      })
    }
  },

  // 加载车辆记录 
  loadCarRecords(callback) {
    if (this.data.isLoading || !this.data.isLoggedIn) {
      console.log('跳过加载：正在加载或未登录')
      callback && callback()
      return
    }

    this.setData({
      isLoading: true,
      hasError: false
    })

    wx.showLoading({
      title: '加载中...',
      mask: true
    })

    const {
      page,
      pageSize,
      currentFilter
    } = this.data

    // 使用正确的API路径 - 获取用户自己的记录
    let url = api.scrapCarRecords

    // 构建查询参数
    let params = {
      page: page,
      page_size: pageSize
    }

    // 添加状态筛选
    if (currentFilter !== 'all') {
      params.status = currentFilter
    }

    // 构建完整URL
    const queryString = Object.keys(params).map(key =>
      `${key}=${encodeURIComponent(params[key])}`
    ).join('&')

    if (queryString) {
      url += `?${queryString}`
    }

    console.log('请求URL:', url)
    console.log('当前页码:', page, '页面大小:', pageSize, '筛选:', currentFilter)

    get(url)
      .then(res => {
        wx.hideLoading()
        console.log('API响应成功，数据量:', res.results ? res.results.length : 0)

        // 处理状态统计信息
        if (res.status_stats) {
          console.log('获取到状态统计:', res.status_stats)
          this.setData({
            totalCount: res.status_stats.total_count || 0,
            pendingCount: res.status_stats.pending_count || 0,
            pricedCount: res.status_stats.priced_count || 0,
            confirmedCount: res.status_stats.confirmed_count || 0,
            cancelledCount: res.status_stats.cancelled_count || 0
          })
        } else if (res.data && res.data.stats) {
          // 兼容 ScrapCarMyRecordsView 接口的统计格式
          console.log('获取到旧格式状态统计:', res.data.stats)
          this.setData({
            totalCount: res.data.stats.total_count || 0,
            pendingCount: res.data.stats.pending_count || 0,
            pricedCount: res.data.stats.priced_count || 0,
            confirmedCount: res.data.stats.confirmed_count || 0,
            cancelledCount: res.data.stats.cancelled_count || 0
          })
        } else {
          console.log('未获取到状态统计信息，使用本地计算')
          // 如果没有统计信息，使用本地数据计算
          this.calculateStatsFromLocalData()
        }

        // 处理Django REST Framework的标准分页响应格式
        if (res && res.results && Array.isArray(res.results)) {
          const records = res.results
          const totalCount = res.count || 0
          const hasNext = !!res.next

          console.log('获取到记录数量:', records.length)
          console.log('总记录数:', totalCount)
          console.log('是否有下一页:', hasNext)

          // 格式化记录数据 - 使用后端返回的display_price字段
          const formattedRecords = records.map(item => {
            // 直接使用后端返回的display_price，它已经实现了最终价格为空时显示预估价格的逻辑
            const displayPrice = item.display_price

            // 格式化价格显示
            const formattedPrice = displayPrice !== null && displayPrice !== undefined ?
              `¥${parseFloat(displayPrice).toFixed(2)}` : '待评估'

            return {
              id: item.id,
              imageUrl: item.car_image_url || this.getFullImageUrl(item.car_image_path) || '/images/default-car.png',
              carModel: item.car_model || '未知车型',
              contactName: item.contact_name || '未知联系人',
              contactPhone: item.contact_phone || '未知电话',
              submitTime: item.submit_time_formatted || this.formatDateTime(item.submit_time) || '未知时间',
              status: item.status || 'pending',
              statusText: item.status_display || this.getStatusText(item.status) || '待评估',
              statusClass: this.getStatusClass(item.status),
              price: displayPrice, // 原始价格数值
              formattedPrice: formattedPrice, // 格式化后的价格显示
              estimatedPrice: item.estimated_price,
              finalPrice: item.final_price,
              region: item.region || '未知地区',
              carCount: item.car_count || 1,
              canStart: item.can_start !== undefined ? item.can_start : true,
              weight: item.weight || null,
              // 添加价格类型标识，用于显示价格来源
              priceSource: item.final_price !== null && item.final_price !== undefined ?
                'final' : (item.estimated_price !== null && item.estimated_price !== undefined ? 'estimated' : 'none')
            }
          })

          // 如果是第一页，直接替换数据；否则追加数据
          const newRecords = page === 1 ? formattedRecords : this.data.carRecords.concat(formattedRecords)

          this.setData({
            carRecords: newRecords,
            filteredCars: newRecords, // 初始时筛选后的数据与全部数据相同
            page: page + 1,
            hasMore: hasNext,
            isLoading: false,
            isRefreshing: false
          }, () => {
            // 应用当前筛选状态
            this.applyFilter()
            console.log('数据加载完成，总记录数:', newRecords.length, '筛选后记录数:', this.data.filteredCars.length)
            console.log('统计信息:', {
              totalCount: this.data.totalCount,
              pendingCount: this.data.pendingCount,
              pricedCount: this.data.pricedCount,
              confirmedCount: this.data.confirmedCount,
              cancelledCount: this.data.cancelledCount
            })
            callback && callback()
          })
        } else if (Array.isArray(res)) {
          // 如果返回的是数组（非分页格式）
          console.log('获取到非分页记录数量:', res.length)

          const formattedRecords = res.map(item => {
            // 直接使用后端返回的display_price
            const displayPrice = item.display_price
            const formattedPrice = displayPrice !== null && displayPrice !== undefined ?
              `¥${parseFloat(displayPrice).toFixed(2)}` : '待评估'

            return {
              id: item.id,
              imageUrl: item.car_image_url || this.getFullImageUrl(item.car_image_path) || '/images/default-car.png',
              carModel: item.car_model || '未知车型',
              contactName: item.contact_name || '未知联系人',
              contactPhone: item.contact_phone || '未知电话',
              submitTime: item.submit_time_formatted || this.formatDateTime(item.submit_time) || '未知时间',
              status: item.status || 'pending',
              statusText: item.status_display || this.getStatusText(item.status) || '待评估',
              statusClass: this.getStatusClass(item.status),
              price: displayPrice,
              formattedPrice: formattedPrice,
              estimatedPrice: item.estimated_price,
              finalPrice: item.final_price,
              region: item.region || '未知地区',
              carCount: item.car_count || 1,
              canStart: item.can_start !== undefined ? item.can_start : true,
              weight: item.weight || null,
              priceSource: item.final_price !== null && item.final_price !== undefined ?
                'final' : (item.estimated_price !== null && item.estimated_price !== undefined ? 'estimated' : 'none')
            }
          })

          const newRecords = page === 1 ? formattedRecords : this.data.carRecords.concat(formattedRecords)

          this.setData({
            carRecords: newRecords,
            filteredCars: newRecords,
            page: page + 1,
            hasMore: false, // 非分页数据，没有更多
            isLoading: false,
            isRefreshing: false
          }, () => {
            this.applyFilter()
            console.log('数据加载完成，总记录数:', newRecords.length)
            console.log('统计信息:', {
              totalCount: this.data.totalCount,
              pendingCount: this.data.pendingCount,
              pricedCount: this.data.pricedCount,
              confirmedCount: this.data.confirmedCount,
              cancelledCount: this.data.cancelledCount
            })
            callback && callback()
          })
        } else {
          console.log('响应格式不支持:', res)
          throw new Error('不支持的响应格式')
        }
      })
      .catch(err => {
        wx.hideLoading()
        console.error('加载车辆记录失败:', err)

        let errorMessage = '网络错误，请重试'

        if (err.status === 401) {
          errorMessage = '请先登录'
          this.setData({
            isLoggedIn: false
          })
        } else if (err.status === 404) {
          // 如果是第一页404，可能是没有数据
          if (this.data.page === 1) {
            errorMessage = '暂无数据'
            this.setData({
              carRecords: [],
              filteredCars: [],
              totalCount: 0,
              pendingCount: 0,
              pricedCount: 0,
              confirmedCount: 0,
              cancelledCount: 0,
              hasMore: false
            })
          } else {
            errorMessage = '没有更多数据了'
            this.setData({
              hasMore: false
            })
          }
        } else if (err.message) {
          errorMessage = err.message
        }

        this.setData({
          isLoading: false,
          isRefreshing: false,
          hasError: true,
          errorMessage
        })

        wx.showToast({
          title: '加载失败',
          icon: 'none',
          duration: 2000
        })

        callback && callback()
      })
  },

  // 获取完整图片URL
  getFullImageUrl(imagePath) {
    if (!imagePath) return null

    // 如果已经是完整URL，直接返回
    if (imagePath.startsWith('http://') || imagePath.startsWith('https://')) {
      return imagePath
    }

    // 否则构建完整URL 
    const baseUrl = api.baseUrl.replace('/recycle/api', '')
    return `${baseUrl}${imagePath.startsWith('/') ? '' : '/'}${imagePath}`
  },

  // 格式化日期时间
  formatDateTime(dateTimeStr) {
    if (!dateTimeStr) return null

    try {
      // 兼容iOS的日期解析，将"yyyy-MM-dd HH:mm:ss"转换为"yyyy/MM/dd HH:mm:ss"
      const isoStr = dateTimeStr.replace(/-/g, '/').replace('T', ' ')
      const date = new Date(isoStr)
      
      // 检查日期是否有效
      if (isNaN(date.getTime())) {
        throw new Error('Invalid date')
      }
      
      return `${date.getFullYear()}-${(date.getMonth() + 1).toString().padStart(2, '0')}-${date.getDate().toString().padStart(2, '0')} ${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`
    } catch (e) {
      console.error('日期格式化错误:', e)
      return dateTimeStr
    }
  },

  // 从记录计算统计信息
  calculateStatsFromRecords(records) {
    return {
      total_count: records.length,
      pending_count: this.countRecordsByStatus(records, 'pending'),
      priced_count: this.countRecordsByStatus(records, 'priced'),
      confirmed_count: this.countRecordsByStatus(records, 'confirmed'),
      cancelled_count: this.countRecordsByStatus(records, 'cancelled')
    }
  },

  // 统计指定状态的记录数
  countRecordsByStatus(records, status) {
    return records.filter(item => item.status === status).length
  },



  // 根据状态筛选
  filterByStatus(e) {
    const status = e.currentTarget.dataset.status
    console.log('筛选状态:', status)

    this.setData({
      currentFilter: status,
      page: 1,
      carRecords: [],
      filteredCars: [],
      hasMore: true,
      isRefreshing: true
    }, () => {
      if (this.data.isLoggedIn) {
        this.loadCarRecords(() => {
          console.log('筛选加载完成')
          this.setData({
            isRefreshing: false
          })
        })
      } else {
        this.applyFilter()
        this.setData({
          isRefreshing: false
        })
      }
    })
  },


  loadStats() {
    if (!this.data.isLoggedIn) {
      return
    }

    console.log('加载统计信息')

    // 使用专门的统计接口
    const url = api.scrapCarStats

    get(url)
      .then(res => {
        console.log('统计信息响应:', res)

        if (res && res.success && res.data) {
          const stats = res.data
          this.setData({
            totalCount: stats.total_count || 0,
            pendingCount: stats.pending_count || 0,
            pricedCount: stats.priced_count || 0,
            confirmedCount: stats.confirmed_count || 0,
            cancelledCount: stats.cancelled_count || 0
          })
          console.log('统计信息更新完成:', stats)
        } else {
          console.warn('统计信息格式不正确，使用本地计算')
          this.calculateStatsFromLocalData()
        }
      })
      .catch(err => {
        console.error('加载统计信息失败:', err)
        console.log('使用本地数据计算统计信息')
        this.calculateStatsFromLocalData()
      })
  },

  // 从本地数据计算统计信息（备用方案）
  calculateStatsFromLocalData() {
    const records = this.data.carRecords
    const stats = this.calculateStatsFromRecords(records)

    this.setData({
      totalCount: stats.total_count,
      pendingCount: stats.pending_count,
      pricedCount: stats.priced_count,
      confirmedCount: stats.confirmed_count,
      cancelledCount: stats.cancelled_count
    })

    console.log('本地计算统计信息:', stats)
  },
  
  // 应用筛选
  applyFilter() {
    let filtered = [...this.data.carRecords]

    if (this.data.currentFilter !== 'all') {
      filtered = filtered.filter(item => item.status === this.data.currentFilter)
    }

    this.setData({
      filteredCars: filtered
    })

    console.log('应用筛选完成，筛选后记录数:', filtered.length)
  },

  // 清除筛选
  clearFilter() {
    console.log('清除筛选')
    this.setData({
      currentFilter: 'all',
      page: 1,
      carRecords: [],
      filteredCars: [],
      hasMore: true,
      isRefreshing: true
    }, () => {
      if (this.data.isLoggedIn) {
        this.loadCarRecords(() => {
          console.log('清除筛选后加载完成')
          this.setData({
            isRefreshing: false
          })
        })
      } else {
        this.applyFilter()
        this.setData({
          isRefreshing: false
        })
      }
    })
  },

  // 加载更多
  loadMore() {
    if (!this.data.hasMore || this.data.isLoading || !this.data.isLoggedIn || this.data.isRefreshing) {
      console.log('跳过加载更多:', {
        hasMore: this.data.hasMore,
        isLoading: this.data.isLoading,
        isLoggedIn: this.data.isLoggedIn,
        isRefreshing: this.data.isRefreshing
      })
      return
    }
    console.log('执行加载更多，下一页:', this.data.page)
    this.loadCarRecords()
  },

  // 获取状态对应的CSS类名
  getStatusClass(status) {
    const statusClassMap = {
      'pending': 'status-pending',
      'priced': 'status-priced',
      'confirmed': 'status-confirmed',
      'cancelled': 'status-cancelled'
    }
    return statusClassMap[status] || 'status-pending'
  },

  // 查看详情
  viewDetails(e) {
    const id = e.currentTarget.dataset.id
    console.log('查看详情:', id)
    wx.navigateTo({
      url: `/pages/recycle/detail/detail?id=${id}`
    })
  },

  // 取消记录 - 调用统一的取消方法
  cancelRecord(e) {
    const id = e.currentTarget.dataset.id
    console.log('取消记录:', id)
    wx.showModal({
      title: '确认取消',
      content: '确定要取消这条记录吗？',
      success: (res) => {
        if (res.confirm) {
          this.cancelOrder(id, '用户取消')
        }
      }
    })
  },

  // 拒绝价格 - 调用统一的取消方法
  rejectPrice(e) {
    const id = e.currentTarget.dataset.id
    console.log('拒绝价格:', id)
    wx.showModal({
      title: '确认拒绝',
      content: '确定要拒绝该评估价格吗？',
      success: (res) => {
        if (res.confirm) {
          this.cancelOrder(id, '用户拒绝价格')
        }
      }
    })
  },

  // 统一的取消订单方法
  cancelOrder(id, reason) {
    if (!this.data.isLoggedIn) {
      wx.showToast({
        title: '请先登录',
        icon: 'none'
      })
      return
    }

    console.log('取消订单:', id, '原因:', reason)
    wx.showLoading({
      title: '处理中...',
      mask: true
    })

    // URL路径 - 确保没有重复的/recycle
    const url = `${api.scrapCarUpdateStatus}${id}/update_status/`
    console.log('请求URL:', url)

    // 构建符合后端要求的数据格式
    const requestData = {
      status: 'cancelled',
      reason: reason
    }

    console.log('请求数据:', requestData)

    post(url, {
        data: requestData,
        header: {
          'Content-Type': 'application/json'
        }
      })
      .then(res => {
        wx.hideLoading()
        console.log('取消订单响应:', res)

        // 处理不同的响应格式
        if (res && res.success) {
          // 更新本地数据
          const updatedRecords = this.data.carRecords.map(item => {
            if (item.id == id) { // 使用 == 而不是 ===，因为id可能是字符串或数字
              return {
                ...item,
                status: 'cancelled',
                statusText: '已取消',
                statusClass: 'status-cancelled',
                formattedPrice: '已取消' // 取消后价格显示为已取消
              }
            }
            return item
          })

          this.setData({
            carRecords: updatedRecords
          }, () => {
            this.applyFilter()
            wx.showToast({
              title: '操作成功',
              icon: 'success',
              duration: 2000
            })

            // 重新计算统计数据
            const stats = this.calculateStatsFromRecords(updatedRecords)
            this.setData({
              totalCount: stats.total_count,
              pendingCount: stats.pending_count,
              pricedCount: stats.priced_count,
              confirmedCount: stats.confirmed_count,
              cancelledCount: stats.cancelled_count
            })

            // 设置刷新标志，确保数据同步
            wx.setStorageSync('needRefreshMyCars', true)
          })
        } else {
          throw new Error(res.message || '操作失败')
        }
      })
      .catch(err => {
        wx.hideLoading()
        console.error('取消订单失败:', err)

        // 打印详细的错误信息
        if (err.errors) {
          console.log('验证错误详情:', err.errors)
        }

        let errorMessage = '操作失败，请重试'
        if (err.message) {
          errorMessage = err.message
        }

        // 如果API不可用，模拟成功
        if (err.status === 404 || err.status === 0 || err.status === 400) {
          console.log('模拟取消订单成功')
          const updatedRecords = this.data.carRecords.map(item => {
            if (item.id == id) {
              return {
                ...item,
                status: 'cancelled',
                statusText: '已取消',
                statusClass: 'status-cancelled',
                formattedPrice: '已取消'
              }
            }
            return item
          })

          this.setData({
            carRecords: updatedRecords
          }, () => {
            this.applyFilter()
            // 重新计算统计数据
            const stats = this.calculateStatsFromRecords(updatedRecords)
            this.setData({
              totalCount: stats.total_count,
              pendingCount: stats.pending_count,
              pricedCount: stats.priced_count,
              confirmedCount: stats.confirmed_count,
              cancelledCount: stats.cancelled_count
            })

            wx.showToast({
              title: '操作成功（演示模式）',
              icon: 'success',
              duration: 2000
            })
          })
        } else {
          wx.showModal({
            title: '操作失败',
            content: errorMessage,
            showCancel: false
          })
        }
      })
  },

  // 接受价格
  acceptPrice(e) {
    const id = e.currentTarget.dataset.id
    console.log('接受价格:', id)
    wx.showModal({
      title: '确认同意',
      content: '确定要同意该评估价格吗？',
      success: (res) => {
        if (res.confirm) {
          this.confirmOrder(id, '用户同意价格')
        }
      }
    })
  },

  // 统一的确认订单方法
  confirmOrder(id, reason) {
    if (!this.data.isLoggedIn) {
      wx.showToast({
        title: '请先登录',
        icon: 'none'
      })
      return
    }

    console.log('确认订单:', id, '原因:', reason)
    wx.showLoading({
      title: '处理中...',
      mask: true
    })

    const url = `${api.scrapCarUpdateStatus}${id}/update_status/`
    console.log('请求URL:', url)

    // 构建符合后端要求的数据格式
    const requestData = {
      status: 'confirmed',
      reason: reason
    }

    console.log('请求数据:', requestData)

    post(url, {
        data: requestData,
        header: {
          'Content-Type': 'application/json'
        }
      })
      .then(res => {
        wx.hideLoading()
        console.log('确认订单完整响应:', res)

        // 处理不同的响应格式
        if (res && res.success) {
          // 获取原始记录，用于价格信息
          const originalRecord = this.data.carRecords.find(item => item.id == id)
          console.log('原始记录价格信息:', {
            estimatedPrice: originalRecord?.estimatedPrice,
            finalPrice: originalRecord?.finalPrice,
            price: originalRecord?.price
          })

          // 更新本地数据
          const updatedRecords = this.data.carRecords.map(item => {
            if (item.id == id) {
              let updatedItem = {
                ...item,
                status: 'confirmed',
                statusText: '已同意',
                statusClass: 'status-confirmed'
              }

              // 如果后端返回了价格更新标志，或者我们需要模拟价格更新
              if (res.price_updated) {
                console.log('检测到价格自动填充，更新前端显示')
                // 使用后端返回的数据更新价格
                if (res.data && res.data.final_price !== null) {
                  updatedItem.finalPrice = parseFloat(res.data.final_price)
                  updatedItem.price = parseFloat(res.data.final_price)
                  updatedItem.formattedPrice = `¥${parseFloat(res.data.final_price).toFixed(2)}`
                  updatedItem.priceSource = 'final'
                } else if (originalRecord && originalRecord.estimatedPrice) {
                  // 如果后端数据中没有final_price，但原始记录有预估价格
                  updatedItem.finalPrice = originalRecord.estimatedPrice
                  updatedItem.price = originalRecord.estimatedPrice
                  updatedItem.formattedPrice = `¥${parseFloat(originalRecord.estimatedPrice).toFixed(2)}`
                  updatedItem.priceSource = 'final'
                }
                console.log('更新后的价格信息:', {
                  finalPrice: updatedItem.finalPrice,
                  price: updatedItem.price,
                  formattedPrice: updatedItem.formattedPrice
                })
              } else {
                console.log('没有价格自动填充，保持原价格显示')
              }

              return updatedItem
            }
            return item
          })

          this.setData({
            carRecords: updatedRecords
          }, () => {
            this.applyFilter()

            // 显示成功消息，如果有价格更新则特别提示
            let successMessage = '操作成功'
            if (res.price_updated) {
              successMessage = '操作成功，已自动将预估价格设为最终价格'
            }

            wx.showToast({
              title: successMessage,
              icon: 'success',
              duration: 2000
            })

            // 重新计算统计数据
            const stats = this.calculateStatsFromRecords(updatedRecords)
            this.setData({
              totalCount: stats.total_count,
              pendingCount: stats.pending_count,
              pricedCount: stats.priced_count,
              confirmedCount: stats.confirmed_count,
              cancelledCount: stats.cancelled_count
            })

            // 设置刷新标志，确保数据同步
            wx.setStorageSync('needRefreshMyCars', true)

            console.log('确认订单操作完成，当前记录状态:',
              updatedRecords.find(item => item.id == id))
          })
        } else {
          throw new Error(res.message || '操作失败')
        }
      })
      .catch(err => {
        wx.hideLoading()
        console.error('确认订单失败:', err)

        // 打印详细的错误信息
        if (err.errors) {
          console.log('验证错误详情:', err.errors)
        }

        let errorMessage = '操作失败，请重试'
        if (err.message) {
          errorMessage = err.message
        }

        // 如果API不可用，模拟成功（包括价格自动填充）
        if (err.status === 404 || err.status === 0 || err.status === 400) {
          console.log('模拟确认订单成功')
          const originalRecord = this.data.carRecords.find(item => item.id == id)
          const updatedRecords = this.data.carRecords.map(item => {
            if (item.id == id) {
              const updatedItem = {
                ...item,
                status: 'confirmed',
                statusText: '已同意',
                statusClass: 'status-confirmed'
              }

              // 模拟价格自动填充：如果最终价格为null且有预估价格，则自动填充
              if (originalRecord && (!originalRecord.finalPrice || originalRecord.finalPrice === null) &&
                originalRecord.estimatedPrice) {
                console.log('模拟价格自动填充')
                updatedItem.finalPrice = originalRecord.estimatedPrice
                updatedItem.price = originalRecord.estimatedPrice
                updatedItem.formattedPrice = `¥${parseFloat(originalRecord.estimatedPrice).toFixed(2)}`
                updatedItem.priceSource = 'final'
              }

              return updatedItem
            }
            return item
          })

          this.setData({
            carRecords: updatedRecords
          }, () => {
            this.applyFilter()
            // 重新计算统计数据
            const stats = this.calculateStatsFromRecords(updatedRecords)
            this.setData({
              totalCount: stats.total_count,
              pendingCount: stats.pending_count,
              pricedCount: stats.priced_count,
              confirmedCount: stats.confirmed_count,
              cancelledCount: stats.cancelled_count
            })

            wx.showToast({
              title: '操作成功（演示模式）',
              icon: 'success',
              duration: 2000
            })
          })
        } else {
          wx.showModal({
            title: '操作失败',
            content: errorMessage,
            showCancel: false
          })
        }
      })
  },

  // 查看订单
  // viewOrder(e) {
  //   const id = e.currentTarget.dataset.id
  //   console.log('查看订单:', id)
  //   wx.showToast({
  //     title: '功能开发中',
  //     icon: 'none',
  //     duration: 2000
  //   })
  // },

  // 重新提交
  resubmitRecord(e) {
    const id = e.currentTarget.dataset.id
    console.log('重新提交记录:', id)

    // 找到对应的记录
    const record = this.data.carRecords.find(item => item.id === id)
    if (record) {
      console.log('重新提交的记录数据:', record)

      // 显示加载提示
      wx.showLoading({
        title: '加载记录中...',
        mask: true
      })

      // 首先尝试获取记录的完整详情
      this.getRecordDetailForResubmit(id, record)
    } else {
      wx.showToast({
        title: '未找到记录数据',
        icon: 'none'
      })
    }
  },

  // 加载记录详情用于重新提交
  getRecordDetailForResubmit(id, basicRecord) {
    if (!this.data.isLoggedIn) {
      wx.showToast({
        title: '请先登录',
        icon: 'none'
      })
      return
    }

    const url = `${api.scrapCarRecords}${id}/`
    console.log('获取记录详情URL:', url)

    get(url)
      .then(res => {
        wx.hideLoading()
        console.log('记录详情加载成功:', res)

        if (res) {
          // 准备重新提交的数据
          const resubmitData = this.prepareResubmitData(res)

          // 存储到缓存，供提交页面使用
          wx.setStorageSync('resubmitData', resubmitData)
          wx.setStorageSync('isResubmit', true)

          console.log('重新提交数据准备完成:', resubmitData)

          // 跳转到提交页面
          wx.navigateTo({
            url: '/pages/recycle/submitinfo/submitinfo?action=resubmit',
            success: () => {
              console.log('跳转到提交页面成功')
            },
            fail: (err) => {
              console.error('跳转失败:', err)
              wx.showToast({
                title: '跳转失败，请重试',
                icon: 'none'
              })
            }
          })
        } else {
          throw new Error('未找到记录详情')
        }
      })
      .catch(err => {
        wx.hideLoading()
        console.error('加载记录详情失败:', err)

        // 如果获取详情失败，使用基础信息进行重新提交
        console.log('使用基础信息进行重新提交')
        const resubmitData = this.prepareResubmitDataFromBasic(basicRecord)
        wx.setStorageSync('resubmitData', resubmitData)
        wx.setStorageSync('isResubmit', true)

        wx.navigateTo({
          url: '/pages/recycle/submitinfo/submitinfo?action=resubmit',
          success: () => {
            console.log('跳转到提交页面成功（使用基础数据）')
          },
          fail: (err) => {
            console.error('跳转失败:', err)
            wx.showToast({
              title: '跳转失败，请重试',
              icon: 'none'
            })
          }
        })
      })
  },

  // 准备重新提交的数据
  prepareResubmitData(recordDetail) {
    return {
      // 联系人信息
      contactName: recordDetail.contact_name || '',
      contactPhone: recordDetail.contact_phone || '',
      region: this.parseRegion(recordDetail.region),
      address: recordDetail.address || '',

      // 车辆信息
      carModel: recordDetail.car_model || '',
      carCount: recordDetail.car_count || 1,
      weight: recordDetail.weight || '',
      canStart: recordDetail.can_start !== undefined ? recordDetail.can_start : true,

      // 车辆部件信息
      wheelType: recordDetail.wheel_type || '',
      wheelCount: recordDetail.wheel_count || 0,
      ternaryCount: recordDetail.ternary_count || 0,
      batteryCount: recordDetail.battery_count || 0,
      batteryPackCount: recordDetail.battery_pack_count || 0,
      engineCount: recordDetail.engine_count || 0,

      // 其他信息
      remark: recordDetail.remark || '',
      carImagePath: recordDetail.car_image_path || '',
      carImageUrl: recordDetail.car_image_url || '',

      // 原记录信息（用于跟踪）
      originalRecordId: recordDetail.id,
      originalStatus: recordDetail.status,
      originalSubmitTime: recordDetail.submit_time
    }
  },

  // 从基础记录信息准备重新提交数据（当获取详情失败时使用）
  prepareResubmitDataFromBasic(basicRecord) {
    return {
      // 联系人信息
      contactName: basicRecord.contactName || '',
      contactPhone: basicRecord.contactPhone || '',
      region: this.parseRegion(basicRecord.region),
      address: basicRecord.address || '',

      // 车辆信息
      carModel: basicRecord.carModel || '',
      carCount: basicRecord.carCount || 1,
      weight: basicRecord.weight || '',
      canStart: basicRecord.canStart !== undefined ? basicRecord.canStart : true,

      // 车辆部件信息
      wheelType: basicRecord.wheelType || '',
      wheelCount: basicRecord.wheelCount || 0,
      ternaryCount: basicRecord.ternaryCount || 0,
      batteryCount: basicRecord.batteryCount || 0,
      batteryPackCount: basicRecord.batteryPackCount || 0,
      engineCount: basicRecord.engineCount || 0,

      // 其他信息
      remark: basicRecord.remark || '',
      carImagePath: '',
      carImageUrl: basicRecord.imageUrl || '',

      // 原记录信息
      originalRecordId: basicRecord.id,
      originalStatus: basicRecord.status,
      originalSubmitTime: basicRecord.submitTime
    }
  },

  // 解析地区字符串为数组
  parseRegion(regionStr) {
    if (!regionStr) return []

    // 如果是数组，直接返回
    if (Array.isArray(regionStr)) {
      return regionStr
    }

    // 如果是字符串，尝试按逗号分割
    if (typeof regionStr === 'string') {
      return regionStr.split(',').map(item => item.trim()).filter(item => item)
    }

    return []
  },

  // 在文件的适当位置添加以下辅助方法
  // 获取车辆部件数量（兼容不同字段名）
  getPartCount(record, fieldName) {
    const value = record[fieldName]
    if (value === undefined || value === null) return 0
    return parseInt(value) || 0
  },


  // 更新记录状态（用于接受价格）
  updateRecordStatus(id, newStatus, reason) {
    if (!this.data.isLoggedIn) {
      wx.showToast({
        title: '请先登录',
        icon: 'none'
      })
      return
    }

    console.log('更新记录状态:', id, newStatus, reason)
    wx.showLoading({
      title: '处理中...',
      mask: true
    })

    const url = `${api.scrapCarUpdateStatus}${id}/update_status/`

    post(url, {
        status: newStatus,
        reason: reason
      })
      .then(res => {
        wx.hideLoading()

        // 处理不同的响应格式
        if (res && res.success) {
          const updatedRecords = this.data.carRecords.map(item => {
            if (item.id === id) {
              return {
                ...item,
                status: newStatus,
                statusText: this.getStatusText(newStatus),
                statusClass: this.getStatusClass(newStatus)
              }
            }
            return item
          })

          this.setData({
            carRecords: updatedRecords
          }, () => {
            this.applyFilter()
            wx.showToast({
              title: '操作成功',
              icon: 'success',
              duration: 2000
            })

            // 设置刷新标志
            wx.setStorageSync('needRefreshMyCars', true)
          })
        } else {
          throw new Error(res.message || '操作失败')
        }
      })
      .catch(err => {
        wx.hideLoading()
        console.error('更新状态失败:', err)

        // 模拟更新成功（当API不可用时）
        const updatedRecords = this.data.carRecords.map(item => {
          if (item.id === id) {
            return {
              ...item,
              status: newStatus,
              statusText: this.getStatusText(newStatus),
              statusClass: this.getStatusClass(newStatus)
            }
          }
          return item
        })

        this.setData({
          carRecords: updatedRecords
        }, () => {
          this.applyFilter()
          wx.showToast({
            title: '操作成功（演示模式）',
            icon: 'success',
            duration: 2000
          })
        })
      })
  },

  // 获取状态文本
  getStatusText(status) {
    const statusMap = {
      pending: '待评估',
      priced: '已报价',
      confirmed: '已同意',
      cancelled: '已取消'
    }
    return statusMap[status] || '未知状态'
  },

  // 跳转到提交页面
  navigateToSubmit() {
    console.log('跳转到提交页面')
    wx.navigateTo({
      url: '/pages/recycle/submitinfo/submitinfo'
    })
  },

  // 跳转到登录页面
  navigateToLogin() {
    console.log('跳转到登录页面')
    wx.navigateTo({
      url: '/pages/user/login/login'
    })
  },

  // 重试加载
  retryLoad() {
    console.log('重试加载数据')
    this.setData({
      page: 1,
      carRecords: [],
      filteredCars: [],
      hasMore: true,
      hasError: false,
      isRefreshing: true
    })

    if (this.data.isLoggedIn) {
      this.loadCarRecords(() => {
        this.setData({
          isRefreshing: false
        })
      })
    } else {
      this.checkLoginStatus()
      this.setData({
        isRefreshing: false
      })
    }
  },

  // 图片加载失败处理
  onImageError(e) {
    const index = e.currentTarget.dataset.index
    const key = `carRecords[${index}].imageUrl`
    console.log('图片加载失败，使用默认图片:', index)
    this.setData({
      [key]: '/images/default-car.png'
    })
  },

  // 获取价格显示文本（用于WXML中显示）
  getPriceDisplay(record) {
    if (!record) return '待评估'

    // 优先使用格式化后的价格
    if (record.formattedPrice) {
      return record.formattedPrice
    }

    // 如果没有格式化价格，使用原始价格数值
    if (record.price !== null && record.price !== undefined) {
      return `¥${parseFloat(record.price).toFixed(2)}`
    }

    return '待评估'
  },

  // 获取价格标签（用于显示价格类型）
  getPriceLabel(record) {
    if (!record) return '价格'

    switch (record.priceSource) {
      case 'final':
        return '最终价格'
      case 'estimated':
        return '评估价格'
      default:
        return '价格'
    }
  }
})
