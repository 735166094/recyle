// pages/mall/checkout/checkout.js
const app = getApp();
import api from '../../../config/settings';

Page({
  data: {
    // 待结算商品
    checkoutItems: [],
    // 选择的地址对象（包含 id, name, phone, full_address, is_default 等）
    selectedAddress: null,
    // 地址列表（用于弹窗选择）
    addressList: [],
    // 是否显示地址选择弹窗
    showAddressSelector: false,
    // 是否正在加载地址列表
    loadingAddresses: false,
    // 已选优惠券（预留）
    selectedCoupon: null,
    // 订单信息
    orderInfo: {
      total_price: 0,      // 商品总额（积分）
      shipping_fee: 0,     // 运费（固定0）
      coupon_discount: 0,  // 优惠抵扣
      final_price: 0,      // 实付积分
      total_quantity: 0,   // 商品总件数
      needs_address: false // 是否需要地址（根据商品判断）
    },
    // 买家备注
    remark: '',
    // 加载状态
    isLoading: true,
    // 购物车项ID列表（从上一页传入）
    cartItemIds: []
  },

  // ---------- 生命周期 ----------
  onLoad(options) {
    // 接收从购物车传过来的购物车项ID列表（JSON字符串）
    if (options.cart_item_ids) {
      try {
        const ids = JSON.parse(options.cart_item_ids);
        this.setData({ cartItemIds: ids });
      } catch (e) {
        console.error('解析购物车项ID失败', e);
      }
    }
    this.loadCheckoutData();
  },

  onShow() {
    // 如果是从地址新增/编辑页面返回，重新加载地址列表并默认选中新地址（可选）
    // 这里简单处理：如果地址选择弹窗是打开的，重新加载列表
    if (this.data.showAddressSelector) {
      this.loadAddressList();
    }
  },

  // ---------- 加载结算数据 ----------
  async loadCheckoutData() {
    // 登录校验
    if (!app.globalData.isLoggedIn) {
      wx.showToast({ title: '请先登录', icon: 'none' });
      setTimeout(() => {
        wx.navigateTo({
          url: `/pages/user/login/login?redirect=/pages/mall/checkout/checkout?cart_item_ids=${JSON.stringify(this.data.cartItemIds)}`
        });
      }, 500);
      return;
    }

    if (!this.data.cartItemIds || this.data.cartItemIds.length === 0) {
      wx.showToast({ title: '没有可结算的商品', icon: 'none' });
      setTimeout(() => wx.navigateBack(), 1500);
      return;
    }

    this.setData({ isLoading: true });

    try {
      // 1. 获取购物车数据
      const cartItems = await this.fetchCartItems();
      // 2. 过滤出选中的商品
      const selectedItems = cartItems.filter(item => this.data.cartItemIds.includes(item.id));
      if (selectedItems.length === 0) {
        throw new Error('购物车商品不存在或已失效');
      }

      // 3. 格式化商品数据
      const formattedItems = this.formatCartItems(selectedItems);
      
      // 4. 判断是否需要地址
      const needsAddress = formattedItems.some(item => item.needs_address !== false);
      
      // 5. 计算总积分和总件数
      const totalPrice = formattedItems.reduce((sum, item) => sum + (item.price * item.quantity), 0);
      const totalQuantity = formattedItems.reduce((sum, item) => sum + item.quantity, 0);

      this.setData({
        checkoutItems: formattedItems,
        orderInfo: {
          total_price: totalPrice,
          shipping_fee: 0,
          coupon_discount: 0,
          final_price: totalPrice,
          total_quantity: totalQuantity,
          needs_address: needsAddress
        },
        isLoading: false
      });

      // 6. 如果需要地址，自动加载默认地址（不阻塞流程）
      if (needsAddress) {
        this.loadDefaultAddressAsync();
      }
    } catch (error) {
      console.error('加载结算数据失败', error);
      wx.showToast({ title: error.message || '加载失败', icon: 'none' });
      this.setData({ isLoading: false });
    }
  },

  // 获取购物车数据（适配多种返回格式）
  fetchCartItems() {
    return new Promise((resolve, reject) => {
      wx.request({
        url: api.cart,
        method: 'GET',
        header: { 'Authorization': 'Bearer ' + app.globalData.token },
        success(res) {
          if (res.statusCode === 200) {
            let items = [];
            if (res.data.data && res.data.data.items) items = res.data.data.items;
            else if (res.data.items) items = res.data.items;
            else if (Array.isArray(res.data)) items = res.data;
            else if (res.data.data && Array.isArray(res.data.data)) items = res.data.data;
            else if (res.data.results) items = res.data.results;
            else items = res.data || [];
            resolve(items);
          } else {
            reject(new Error('获取购物车失败'));
          }
        },
        fail: reject
      });
    });
  },

  // 格式化购物车项 → 适配兑换接口
  formatCartItems(items) {
    return items.map(item => ({
      id: item.id,
      product_id: item.product_id,
      product_name: item.product_name || '商品',
      product_points: item.price || 0,
      quantity: item.quantity,
      price: item.price || 0,
      needs_address: item.needs_address !== false,
      spec_display: item.spec_display || '默认规格',
      product_image: item.product_image || '/static/tabbar/mall.png',
      stock: item.stock || 0,
      is_available: item.is_available !== false
    }));
  },

  // ---------- 地址相关 ----------
  // 打开地址选择弹窗
  selectAddress() {
    this.setData({ showAddressSelector: true });
    this.loadAddressList();
  },

  // 关闭地址选择弹窗
  closeAddressSelector() {
    this.setData({ showAddressSelector: false });
  },

  // 加载地址列表（用于弹窗）
  loadAddressList() {
    const token = wx.getStorageSync('token');
    if (!token) {
      wx.showToast({ title: '请先登录', icon: 'none' });
      return;
    }

    this.setData({ loadingAddresses: true });

    wx.request({
      url: api.userAddresses,
      method: 'GET',
      header: { 'Authorization': `Bearer ${token}` },
      success: (res) => {
        if (res.statusCode === 200 && res.data.code === 200) {
          const addresses = res.data.data.map(addr => {
            const region_display = [addr.province, addr.city, addr.district].filter(Boolean).join(' ');
            const full_address = addr.full_address || 
              `${addr.province || ''}${addr.city || ''}${addr.district || ''}${addr.detail_address || ''}`;
            return {
              ...addr,
              region_display,
              full_address
            };
          });
          this.setData({
            addressList: addresses,
            loadingAddresses: false
          });
        } else {
          console.error('获取地址失败', res.data);
          this.setData({ loadingAddresses: false });
          wx.showToast({ title: res.data?.message || '获取地址失败', icon: 'none' });
        }
      },
      fail: (err) => {
        console.error('加载地址失败', err);
        this.setData({ loadingAddresses: false });
        wx.showToast({ title: '网络错误', icon: 'none' });
      }
    });
  },

  // 异步加载默认地址（不阻塞结算页面加载）
  async loadDefaultAddressAsync() {
    const token = wx.getStorageSync('token');
    if (!token) return;
    wx.request({
      url: api.userAddresses,
      method: 'GET',
      header: { 'Authorization': `Bearer ${token}` },
      success: (res) => {
        if (res.statusCode === 200 && res.data.code === 200) {
          const addresses = res.data.data || [];
          const defaultAddr = addresses.find(addr => addr.is_default);
          if (defaultAddr) {
            this.setData({
              selectedAddress: this.formatAddressForDisplay(defaultAddr)
            });
          } else if (addresses.length > 0) {
            // 如果没有默认地址，默认选第一个
            this.setData({
              selectedAddress: this.formatAddressForDisplay(addresses[0])
            });
          }
        }
      }
    });
  },

  // 格式化地址用于展示
  formatAddressForDisplay(addr) {
    return {
      id: addr.id,
      name: addr.receiver_name,
      phone: addr.receiver_phone,
      full_address: addr.full_address || 
        `${addr.province || ''}${addr.city || ''}${addr.district || ''}${addr.detail_address || ''}`,
      is_default: addr.is_default,
      province: addr.province,
      city: addr.city,
      district: addr.district,
      detail_address: addr.detail_address
    };
  },

  // 选择地址项
  selectAddressItem(e) {
    const address = e.currentTarget.dataset.address;
    const formatted = this.formatAddressForDisplay(address);
    this.setData({
      selectedAddress: formatted,
      showAddressSelector: false
    });
  },

  // 跳转到新增地址页面
  goToAddAddress() {
    wx.navigateTo({
      url: '/pages/user/address/address?source=checkout',
      success: () => {
        // 关闭当前弹窗，返回后通过 onShow 重新加载
        this.setData({ showAddressSelector: false });
      }
    });
  },

  // ---------- 优惠券（预留）----------
  selectCoupon() {
    wx.showToast({ title: '优惠券功能开发中', icon: 'none' });
  },

  // ---------- 备注 ----------
  onRemarkInput(e) {
    this.setData({ remark: e.detail.value });
  },

  // ---------- 提交订单 ----------
  async submitOrder() {
    const { checkoutItems, selectedAddress, orderInfo, cartItemIds } = this.data;

    // 基础校验
    if (!checkoutItems.length) {
      wx.showToast({ title: '没有可结算的商品', icon: 'none' });
      return;
    }

    // 地址校验（如果需要地址）
    if (orderInfo.needs_address && !selectedAddress) {
      wx.showToast({ title: '请选择收货地址', icon: 'none' });
      return;
    }

    // 积分预检
    wx.showLoading({ title: '校验积分...', mask: true });
    try {
      const userPoints = await this.getUserPoints();
      if (userPoints < orderInfo.final_price) {
        wx.hideLoading();
        wx.showModal({
          title: '积分不足',
          content: `您当前可用积分 ${userPoints}，需要 ${orderInfo.final_price} 积分`,
          showCancel: false
        });
        return;
      }
    } catch (error) {
      wx.hideLoading();
      wx.showToast({ title: '积分查询失败', icon: 'none' });
      return;
    }

    wx.hideLoading();
    wx.showModal({
      title: '确认订单',
      content: `共 ${orderInfo.total_quantity} 件商品，需支付 ${orderInfo.final_price} 积分`,
      success: async (res) => {
        if (res.confirm) {
          await this.performExchange();
        }
      }
    });
  },

  // 获取用户当前可用积分
  getUserPoints() {
    return new Promise((resolve, reject) => {
      wx.request({
        url: api.pointsSummary,
        method: 'GET',
        header: { 'Authorization': 'Bearer ' + app.globalData.token },
        success: (res) => {
          if (res.statusCode === 200 && res.data.data) {
            const points = res.data.data.available_points || res.data.data.total_points || 0;
            resolve(points);
          } else {
            reject(new Error('获取积分失败'));
          }
        },
        fail: reject
      });
    });
  },

  // 串行执行积分兑换
  async performExchange() {
    wx.showLoading({ title: '兑换中...', mask: true });

    const { checkoutItems, selectedAddress } = this.data;
    const successIds = [];
    const failedItems = [];

    for (const item of checkoutItems) {
      try {
        const params = {
          product_id: String(item.product_id),
          product_name: item.product_name,
          product_points: item.product_points,
          quantity: item.quantity
        };

        // 只有需要地址的商品才传 address_id
        if (item.needs_address && selectedAddress) {
          params.address_id = selectedAddress.id;
        }

        const res = await this.requestExchange(params);
        
        if (res.code === 200 || res.status === 200 || res.statusCode === 200) {
          successIds.push(item.id);
        } else {
          failedItems.push({
            name: item.product_name,
            reason: res.message || '兑换失败'
          });
          break; // 失败即停止
        }
      } catch (error) {
        failedItems.push({
          name: item.product_name,
          reason: error.message || '网络异常'
        });
        break;
      }
    }

    wx.hideLoading();

    if (failedItems.length === 0) {
      wx.showToast({ title: '兑换成功', icon: 'success', duration: 2000 });
      
      // 删除已结算的购物车项
      this.clearCartItems(successIds);

      // 跳转到积分记录页面（根据实际项目调整）
      setTimeout(() => {
        wx.redirectTo({
          url: '/pages/mall/order/list/list?type=points'
        });
      }, 1500);
    } else {
      const failMsg = failedItems.map(f => `${f.name}：${f.reason}`).join('；');
      wx.showModal({
        title: '兑换失败',
        content: failMsg,
        showCancel: false,
        success: () => {
          wx.navigateBack();
        }
      });
    }
  },

  // 封装兑换请求
  requestExchange(params) {
    return new Promise((resolve, reject) => {
      wx.request({
        url: api.pointsExchange,
        method: 'POST',
        header: {
          'Authorization': 'Bearer ' + app.globalData.token,
          'Content-Type': 'application/json'
        },
        data: params,
        success: (res) => {
          if (res.statusCode === 200) {
            resolve(res.data);
          } else {
            reject(new Error(res.data.message || '请求失败'));
          }
        },
        fail: reject
      });
    });
  },

  // 删除已结算的购物车项
  clearCartItems(cartItemIds) {
    if (!cartItemIds || cartItemIds.length === 0) return;
    wx.request({
      url: api.cart + 'batch_delete/',
      method: 'POST',
      header: { 'Authorization': 'Bearer ' + app.globalData.token },
      data: { ids: cartItemIds },
      complete: () => {
        // 通知购物车页面刷新
        const pages = getCurrentPages();
        const cartPage = pages.find(p => p.route === 'pages/mall/cart/cart');
        if (cartPage && typeof cartPage.loadCart === 'function') {
          cartPage.loadCart();
        }
      }
    });
  }
});