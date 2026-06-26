const app = getApp();
import api from '../../../config/settings';

Page({
  data: {
    cartData: [], // 购物车数据
    allChecked: false, // 全选状态
    totalQuantity: 0, // 总数量
    selectedCount: 0, // 选中商品数量
    isEditing: false, // 是否编辑模式
    startX: 0, // 触摸起始X坐标
    actionWidth: 450, // 滑动操作区域宽度
    totalPrice: 0, // 选中商品总价
    isLoading: true, // 加载状态
    selectedIds: [], // 选中的购物车项ID
  },

  onLoad() {
    // 页面加载时获取购物车数据
    this.loadCartData();
  },

  onShow() {
    // 页面显示时重新加载购物车数据
    this.loadCartData();
  },

  // 加载购物车数据
  loadCartData() {
    if (!app.globalData.isLoggedIn) {
      this.setData({
        isLoading: false
      });

      wx.showModal({
        title: '提示',
        content: '请先登录',
        confirmText: '去登录',
        success: (res) => {
          if (res.confirm) {
            wx.navigateTo({
              url: '/pages/user/login/login?redirect=/pages/mall/cart/cart'
            });
          } else {
            wx.switchTab({
              url: '/pages/index/index'
            });
          }
        }
      });
      return;
    }

    this.setData({
      isLoading: true
    });

    const that = this;

    wx.request({
      url: api.cart,
      method: 'GET',
      header: {
        'Authorization': 'Bearer ' + app.globalData.token,
        'Content-Type': 'application/json'
      },
      success: function (res) {
        console.log('购物车数据响应:', res);

        if (res.statusCode === 200) {
          let cartItems = [];

          // 处理不同的响应格式
          if (res.data.code === 200 && res.data.data && res.data.data.items) {
            // 格式1: {code: 200, data: {items: [...], stats: {...}}}
            cartItems = res.data.data.items;
            console.log('格式1: 通过data.items获取');
          } else if (res.data.code === 200 && res.data.data && res.data.data.results) {
            // 格式2: {code: 200, data: {results: [...], count: ...}}
            cartItems = res.data.data.results;
            console.log('格式2: 通过data.results获取');
          } else if (res.data.results) {
            // 格式3: {results: [...], count: ...}
            cartItems = res.data.results;
            console.log('格式3: 通过results获取');
          } else if (Array.isArray(res.data)) {
            // 格式4: 直接返回数组
            cartItems = res.data;
            console.log('格式4: 直接返回数组');
          }

          console.log('原始购物车数据:', cartItems);

          // 格式化购物车数据
          const formattedData = cartItems.map(item => {
            console.log('处理购物车项:', item);

            // 直接使用分作为价格
            const priceNum = item.price || item.final_price || 0;
            const priceDisplay = priceNum ? `¥${priceNum}` : '¥0';

            // 如果有原价，也直接使用分
            let originalPrice = '';
            if (item.original_price) {
              originalPrice = `¥${item.original_price}`;
            }
            return {
              id: item.id,
              productId: item.product_id,
              title: item.product_name || item.name || '未知商品',
              spec: item.spec_display || item.get_spec_display || '默认规格',
              price: `¥${priceNum}`,
              priceNum: priceNum,
              originalPrice: item.original_price ? `¥${item.original_price}` : '',
              imgUrl: item.product_image || item.image || '/static/images/default-goods.png',
              quantity: item.quantity || 1,
              checked: false,
              collected: false,
              x: 0,
              stock: item.stock || 0,
              is_available: item.is_available !== false,
              selected_specs: item.selected_specs || {}
            };
          });

          console.log('格式化后的购物车数据:', formattedData);

          that.setData({
            cartData: formattedData,
            isLoading: false
          }, () => {
            that.calculateTotal();
            that.checkAllStatus();
          });
        } else if (res.statusCode === 401) {
          // Token失效
          that.handleTokenExpired();
        } else {
          console.error('加载购物车失败:', res);
          that.setData({
            isLoading: false
          });
          wx.showToast({
            title: '加载购物车失败',
            icon: 'none',
            duration: 2000
          });
        }
      },
      fail: function (err) {
        console.error('加载购物车失败', err);
        that.setData({
          isLoading: false
        });
        wx.showToast({
          title: '网络错误，请检查网络连接',
          icon: 'none',
          duration: 2000
        });
      }
    });
  },

  handleTokenExpired() {
    // 清除本地存储的token
    wx.removeStorageSync('token');
    wx.removeStorageSync('userInfo');
    app.globalData.isLoggedIn = false;
    app.globalData.token = null;
    app.globalData.userInfo = null;

    this.setData({
      isLoading: false
    });

    wx.showModal({
      title: '提示',
      content: '登录已过期，请重新登录',
      confirmText: '重新登录',
      success: (res) => {
        if (res.confirm) {
          wx.navigateTo({
            url: '/pages/user/login/login?redirect=/pages/mall/cart/cart'
          });
        }
      }
    });
  },

  // 计算总价和总数量
  calculateTotal() {
    const {
      cartData
    } = this.data;
    let totalPrice = 0;
    let totalQuantity = 0;
    let selectedCount = 0;
    const selectedIds = [];

    cartData.forEach(item => {
      if (item.checked && item.is_available) {
        totalPrice += item.priceNum * item.quantity;
        totalQuantity += item.quantity;
        selectedCount++;
        selectedIds.push(item.id);
      }
    });

    this.setData({
      totalPrice: `¥${totalPrice}`,
      totalQuantity,
      selectedCount,
      selectedIds
    });
  },

  // 检查全选状态
  checkAllStatus() {
    const {
      cartData
    } = this.data;
    if (cartData.length === 0) {
      this.setData({
        allChecked: false
      });
      return;
    }

    // 只检查可用的商品
    const availableItems = cartData.filter(item => item.is_available);
    if (availableItems.length === 0) {
      this.setData({
        allChecked: false
      });
      return;
    }

    const allChecked = availableItems.every(item => item.checked);
    console.log('检查全选状态:', {
      allChecked,
      availableItems: availableItems.length
    });

    this.setData({
      allChecked
    });
  },

  // 切换单个商品选中状态
  toggleItemCheck(e) {
    console.log('切换单个商品选中状态:', e);
    const index = e.currentTarget.dataset.index;
    const {
      cartData
    } = this.data;

    // 只有可用的商品才能被选中
    if (!cartData[index].is_available) {
      wx.showToast({
        title: '该商品已失效',
        icon: 'none',
        duration: 1500
      });
      return;
    }

    // 切换选中状态
    const newChecked = !cartData[index].checked;

    // 创建新的购物车数据数组
    const newCartData = cartData.map((item, i) => {
      if (i === index) {
        return {
          ...item,
          checked: newChecked
        };
      }
      return item;
    });

    this.setData({
      cartData: newCartData
    }, () => {
      this.calculateTotal();
      this.checkAllStatus();
    });
  },

  // 切换全选状态
  toggleAllCheck() {
    console.log('切换全选状态');
    const {
      allChecked,
      cartData
    } = this.data;
    const newChecked = !allChecked;

    const newCartData = cartData.map(item => {
      // 只有可用的商品才能被选中
      if (item.is_available) {
        return {
          ...item,
          checked: newChecked
        };
      }
      return {
        ...item,
        x: 0
      }; // 重置滑动位置
    });

    console.log('全选状态:', {
      old: allChecked,
      new: newChecked
    });

    this.setData({
      cartData: newCartData,
      allChecked: newChecked
    }, () => {
      this.calculateTotal();
    });
  },

  // 减少商品数量
  decreaseQuantity(e) {
    const index = e.currentTarget.dataset.index;
    const {
      cartData
    } = this.data;
    const cartItem = cartData[index];

    if (cartItem.quantity <= 1) {
      return;
    }

    const newQuantity = cartItem.quantity - 1;
    this.updateCartItemQuantity(cartItem.id, newQuantity, index);
  },

  // 增加商品数量
  increaseQuantity(e) {
    const index = e.currentTarget.dataset.index;
    const {
      cartData
    } = this.data;
    const cartItem = cartData[index];
    const newQuantity = cartItem.quantity + 1;

    // 检查库存
    if (newQuantity > cartItem.stock) {
      wx.showToast({
        title: '库存不足',
        icon: 'none',
        duration: 1500
      });
      return;
    }

    this.updateCartItemQuantity(cartItem.id, newQuantity, index);
  },

  // 更新购物车项数量
  updateCartItemQuantity(cartItemId, quantity, index) {
    const that = this;

    wx.request({
      url: api.cart + cartItemId + '/',
      method: 'PATCH',
      header: {
        'Authorization': 'Bearer ' + app.globalData.token,
        'Content-Type': 'application/json'
      },
      data: {
        quantity: quantity
      },
      success: function (res) {
        console.log('更新数量响应:', res);
        if (res.statusCode === 200) {
          // 更新前端数据
          const cartData = that.data.cartData;
          cartData[index].quantity = quantity;
          that.setData({
            cartData
          }, () => {
            that.calculateTotal();
          });

          wx.showToast({
            title: '更新成功',
            icon: 'success',
            duration: 1000
          });
        } else if (res.statusCode === 404) {
          wx.showToast({
            title: '商品不存在',
            icon: 'none'
          });
        } else {
          wx.showToast({
            title: res.data.message || '更新失败',
            icon: 'none'
          });
        }
      },
      fail: function (err) {
        console.error('更新数量失败', err);
        wx.showToast({
          title: '网络错误',
          icon: 'none'
        });
      }
    });
  },

  // 触摸开始
  onTouchStart(e) {
    this.setData({
      startX: e.changedTouches[0].clientX
    });

    const {
      cartData
    } = this.data;
    const currentIndex = e.currentTarget.dataset.index;

    cartData.forEach((item, index) => {
      if (index !== currentIndex) {
        item.x = 0;
      }
    });

    this.setData({
      cartData
    });
  },

  // 触摸结束
  onTouchEnd(e) {
    const {
      startX,
      actionWidth,
      cartData
    } = this.data;
    const currentX = e.changedTouches[0].clientX;
    const index = e.currentTarget.dataset.index;
    const diffX = startX - currentX;

    if (diffX > actionWidth / 3) {
      cartData[index].x = -actionWidth;
    } else {
      cartData[index].x = 0;
    }

    this.setData({
      cartData
    });
  },

  // 切换收藏状态
  toggleCollection(e) {
    const index = e.currentTarget.dataset.index;
    const {
      cartData
    } = this.data;

    cartData[index].collected = !cartData[index].collected;
    cartData[index].x = 0;

    // 实际项目中应该调用收藏API
    wx.showToast({
      title: cartData[index].collected ? '收藏成功' : '取消收藏',
      icon: 'none',
      duration: 1500
    });

    this.setData({
      cartData
    });
  },

  // 找相似商品
  findSimilar(e) {
    const index = e.currentTarget.dataset.index;
    const {
      cartData
    } = this.data;
    const goods = cartData[index];

    cartData[index].x = 0;
    this.setData({
      cartData
    });

    // 跳转到相似商品页面
    wx.navigateTo({
      url: `/pages/mall/search/search?keyword=${encodeURIComponent(goods.title)}`
    });
  },

  // 删除单个商品
  deleteItem(e) {
    const index = e.currentTarget.dataset.index;
    const {
      cartData
    } = this.data;
    const goods = cartData[index];

    wx.showModal({
      title: '确认删除',
      content: `确定要删除"${goods.title}"吗？`,
      confirmColor: '#F53F3F',
      success: (res) => {
        if (res.confirm) {
          this.deleteCartItem(goods.id, index);
        } else {
          cartData[index].x = 0;
          this.setData({
            cartData
          });
        }
      }
    });
  },

  // 删除购物车项
  deleteCartItem(cartItemId, index) {
    const that = this;

    wx.request({
      url: api.cart + cartItemId + '/',
      method: 'DELETE',
      header: {
        'Authorization': 'Bearer ' + app.globalData.token
      },
      success: function (res) {
        console.log('删除响应:', res);
        if (res.statusCode === 204 || res.statusCode === 200) {
          const cartData = that.data.cartData;
          cartData.splice(index, 1);

          that.setData({
            cartData
          }, () => {
            that.calculateTotal();
            that.checkAllStatus();
          });

          wx.showToast({
            title: '删除成功',
            icon: 'success',
            duration: 1500
          });
        } else {
          wx.showToast({
            title: '删除失败',
            icon: 'none'
          });
        }
      },
      fail: function (err) {
        console.error('删除失败', err);
        wx.showToast({
          title: '网络错误',
          icon: 'none'
        });
      }
    });
  },

  // 切换编辑模式
  toggleEditMode() {
    const {
      isEditing,
      cartData
    } = this.data;

    cartData.forEach(item => {
      item.x = 0;
    });

    this.setData({
      isEditing: !isEditing,
      cartData
    });
  },

  // 删除选中商品
  deleteSelected() {
    const {
      selectedIds
    } = this.data;

    if (selectedIds.length === 0) {
      wx.showToast({
        title: '请选择要删除的商品',
        icon: 'none',
        duration: 1500
      });
      return;
    }

    wx.showModal({
      title: '确认删除',
      content: `确定要删除选中的${selectedIds.length}件商品吗？`,
      confirmColor: '#F53F3F',
      success: (res) => {
        if (res.confirm) {
          this.batchDeleteCartItems(selectedIds);
        }
      }
    });
  },

  // 批量删除购物车项
  batchDeleteCartItems(ids) {
    const that = this;

    wx.request({
      url: api.cart + 'batch_delete/',
      method: 'POST',
      header: {
        'Authorization': 'Bearer ' + app.globalData.token,
        'Content-Type': 'application/json'
      },
      data: {
        ids: ids
      },
      success: function (res) {
        console.log('批量删除响应:', res);
        if (res.statusCode === 200) {
          wx.showToast({
            title: `已删除${ids.length}件商品`,
            icon: 'success',
            duration: 1500
          });

          // 重新加载购物车数据
          that.loadCartData();

          // 退出编辑模式
          that.setData({
            isEditing: false
          });
        } else {
          wx.showToast({
            title: res.data.message || '删除失败',
            icon: 'none'
          });
        }
      },
      fail: function (err) {
        console.error('批量删除失败', err);
        wx.showToast({
          title: '网络错误',
          icon: 'none'
        });
      }
    });
  },

  // 前往结算
  goToCheckout() {
    const {
      totalQuantity,
      selectedIds
    } = this.data;

    if (totalQuantity === 0) {
      wx.showToast({
        title: '请选择要结算的商品',
        icon: 'none',
        duration: 1500
      });
      return;
    }

    // 检查是否有失效商品
    const invalidItems = this.data.cartData.filter(item =>
      item.checked && !item.is_available
    );

    if (invalidItems.length > 0) {
      wx.showModal({
        title: '提示',
        content: '选中的商品中有失效商品，无法结算',
        showCancel: false
      });
      return;
    }

    // 跳转到结算页面，传递选中的购物车项ID
    wx.navigateTo({
      url: `/pages/mall/checkout/checkout?cart_item_ids=${JSON.stringify(selectedIds)}`
    });
  },

  // 前往购物
  goToShopping() {
    wx.switchTab({
      url: '/pages/mall/index/index'
    });
  },

  // 前往商品详情
  navigateToDetail(e) {
    const id = e.currentTarget.dataset.id;
    wx.navigateTo({
      url: `/pages/mall/goodsdetail/goodsdetail?id=${id}`
    });
  },

  // 前往我的地址
  gotoMyAddress() {
    if (!app.globalData.isLoggedIn) {
      wx.showModal({
        title: '提示',
        content: '请先登录',
        confirmText: '去登录',
        success: (res) => {
          if (res.confirm) {
            wx.navigateTo({
              url: '/pages/user/login/login?redirect=/pages/mall/cart/cart'
            });
          }
        }
      });
      return;
    }

    wx.navigateTo({
      url: '/pages/user/address/address',
    });
  },

  // 下拉刷新
  onPullDownRefresh() {
    this.loadCartData();
    setTimeout(() => {
      wx.stopPullDownRefresh();
    }, 1000);
  }
});