Page({
  data: {
    // 购物车商品列表
    cartItems: [],
    // 全选状态
    selectAll: false,
    // 选中的商品数量
    selectedCount: 0,
    // 选中的商品总价
    totalPrice: 0,
    // 是否编辑状态
    editMode: false
  },

  onShow() {
    // 每次显示页面时加载购物车数据
    this.loadCartData();
  },

  // 加载购物车数据
  loadCartData() {
    // 从本地存储获取购物车数据
    const cartData = wx.getStorageSync('cartData') || [];
    
    // 为每个商品添加选中状态
    const cartItems = cartData.map(item => ({
      ...item,
      selected: true // 默认选中
    }));
    
    this.setData({
      cartItems: cartItems
    });
    
    // 更新选中状态和总价
    this.updateSelectedStatus();
  },

  // 从后端获取购物车数据的预留方法
  fetchCartDataFromBackend() {
    // 实际项目中，应从后端获取当前用户的购物车数据
    wx.request({
      url: 'https://your-backend-url.com/api/cart',
      method: 'GET',
      header: {
        // 通常需要携带用户身份标识
        'Authorization': 'Bearer ' + wx.getStorageSync('token')
      },
      success: (res) => {
        if (res.data.success) {
          const cartItems = res.data.data.map(item => ({
            ...item,
            selected: true
          }));
          
          this.setData({
            cartItems: cartItems
          });
          
          this.updateSelectedStatus();
        }
      },
      fail: (err) => {
        console.error('获取购物车数据失败', err);
      }
    });
  },

  // 更新选中状态和总价
  updateSelectedStatus() {
    const { cartItems } = this.data;
    
    // 计算选中的商品数量和总价
    let selectedCount = 0;
    let totalPrice = 0;
    
    cartItems.forEach(item => {
      if (item.selected) {
        selectedCount += item.quantity;
        totalPrice += parseFloat(item.price) * item.quantity;
      }
    });
    
    // 判断是否全选
    const selectAll = cartItems.length > 0 && cartItems.every(item => item.selected);
    
    this.setData({
      selectedCount,
      totalPrice: totalPrice.toFixed(2),
      selectAll
    });
  },

  // 切换商品选中状态
  toggleSelect(e) {
    const index = e.currentTarget.dataset.index;
    const { cartItems } = this.data;
    
    cartItems[index].selected = !cartItems[index].selected;
    
    this.setData({
      cartItems: cartItems
    });
    
    this.updateSelectedStatus();
  },

  // 全选/取消全选
  toggleSelectAll() {
    const { selectAll, cartItems } = this.data;
    const newSelectAll = !selectAll;
    
    // 更新所有商品的选中状态
    const newCartItems = cartItems.map(item => ({
      ...item,
      selected: newSelectAll
    }));
    
    this.setData({
      cartItems: newCartItems,
      selectAll: newSelectAll
    });
    
    this.updateSelectedStatus();
  },

  // 减少商品数量
  decreaseQuantity(e) {
    const index = e.currentTarget.dataset.index;
    const { cartItems } = this.data;
    
    if (cartItems[index].quantity > 1) {
      cartItems[index].quantity -= 1;
    } else {
      // 数量为1时再减少则删除该商品
      this.removeItem(index);
      return;
    }
    
    this.setData({
      cartItems: cartItems
    });
    
    // 更新本地存储
    this.saveCartData();
    // 更新选中状态和总价
    this.updateSelectedStatus();
  },

  // 增加商品数量
  increaseQuantity(e) {
    const index = e.currentTarget.dataset.index;
    const { cartItems } = this.data;
    
    cartItems[index].quantity += 1;
    
    this.setData({
      cartItems: cartItems
    });
    
    // 更新本地存储
    this.saveCartData();
    // 更新选中状态和总价
    this.updateSelectedStatus();
  },

  // 手动输入数量
  inputQuantity(e) {
    const index = e.currentTarget.dataset.index;
    const value = parseInt(e.detail.value) || 1;
    const { cartItems } = this.data;
    
    cartItems[index].quantity = value;
    
    this.setData({
      cartItems: cartItems
    });
    
    // 更新本地存储
    this.saveCartData();
    // 更新选中状态和总价
    this.updateSelectedStatus();
  },

  // 删除商品
  removeItem(index) {
    const { cartItems } = this.data;
    
    // 显示确认对话框
    wx.showModal({
      title: '提示',
      content: '确定要从购物车中移除该商品吗？',
      success: (res) => {
        if (res.confirm) {
          // 用户确认删除
          cartItems.splice(index, 1);
          
          this.setData({
            cartItems: cartItems
          });
          
          // 更新本地存储
          this.saveCartData();
          // 更新选中状态和总价
          this.updateSelectedStatus();
          
          wx.showToast({
            title: '已移除',
            icon: 'none',
            duration: 1500
          });
        }
      }
    });
  },

  // 保存购物车数据到本地存储
  saveCartData() {
    // 移除selected属性，只保存必要数据
    const cartData = this.data.cartItems.map(({ selected, ...rest }) => rest);
    wx.setStorageSync('cartData', cartData);
    
    // 同步到后端的预留方法
    this.syncCartToBackend(cartData);
  },

  // 同步购物车数据到后端的预留方法
  syncCartToBackend(cartData) {
    // 实际项目中，应将购物车数据同步到后端
    wx.request({
      url: 'https://your-backend-url.com/api/cart',
      method: 'POST',
      header: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + wx.getStorageSync('token')
      },
      data: {
        items: cartData
      },
      success: (res) => {
        if (!res.data.success) {
          console.error('同步购物车数据失败', res.data.message);
        }
      },
      fail: (err) => {
        console.error('同步购物车数据到后端失败', err);
      }
    });
  },

  // 切换编辑模式
  toggleEditMode() {
    this.setData({
      editMode: !this.data.editMode
    });
  },

  // 删除选中的商品
  deleteSelectedItems() {
    const { cartItems } = this.data;
    const selectedItems = cartItems.filter(item => item.selected);
    
    if (selectedItems.length === 0) {
      wx.showToast({
        title: '请选择要删除的商品',
        icon: 'none',
        duration: 1500
      });
      return;
    }
    
    wx.showModal({
      title: '提示',
      content: `确定要删除选中的${selectedItems.length}件商品吗？`,
      success: (res) => {
        if (res.confirm) {
          // 保留未选中的商品
          const newCartItems = cartItems.filter(item => !item.selected);
          
          this.setData({
            cartItems: newCartItems,
            editMode: false
          });
          
          // 更新本地存储
          this.saveCartData();
          // 更新选中状态和总价
          this.updateSelectedStatus();
          
          wx.showToast({
            title: `已删除${selectedItems.length}件商品`,
            icon: 'none',
            duration: 1500
          });
        }
      }
    });
  },

  // 结算
  checkout() {
    const { selectedCount } = this.data;
    
    if (selectedCount === 0) {
      wx.showToast({
        title: '请选择要结算的商品',
        icon: 'none',
        duration: 1500
      });
      return;
    }
    
    // 获取选中的商品
    const selectedItems = this.data.cartItems
      .filter(item => item.selected)
      .map(({ selected, ...rest }) => rest);
    
    // 跳转到结算页面，并携带选中的商品信息
    wx.navigateTo({
      url: `/pages/checkout/checkout?items=${encodeURIComponent(JSON.stringify(selectedItems))}`
    });
  },

  // 跳转到商品详情
  goToGoodDetail(e) {
    const goodsId = e.currentTarget.dataset.id;
    wx.navigateTo({
      url: `/pages/gooddetail/gooddetail?id=${goodsId}`
    });
  },

  // 继续购物
  continueShopping() {
    wx.navigateBack({
      delta: 1 // 返回上一级页面，通常是商城首页
    });
  }
});
