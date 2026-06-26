import api from '../../../config/settings'

Page({
  data: {
    addresses: [],
    showAddDialog: false,
    editMode: false,
    currentAddressId: null,
    newAddress: {
      receiver_name: '',
      receiver_phone: '',
      country: '中国',
      province: '',
      city: '',
      district: '',
      detail_address: '',
      postal_code: '',
      address_tag: 'home',
      is_default: false
    },
    tagOptions: [{
        value: 'home',
        label: '家'
      },
      {
        value: 'company',
        label: '公司'
      },
      {
        value: 'school',
        label: '学校'
      },
      {
        value: 'other',
        label: '其他'
      }
    ],
    userInfo: null,
    region: [], // 用于picker的数组格式
    loading: false
  },

  onLoad() {
    console.log('address1页面加载');
    this.loadUserInfo();
    this.loadAddresses();
  },

  onShow() {
    console.log('address1页面显示');
    this.loadAddresses();
  },

  // 加载用户信息
  loadUserInfo() {
    const userInfo = wx.getStorageSync('userInfo');
    console.log('加载用户信息:', userInfo);
    if (userInfo) {
      this.setData({
        userInfo: userInfo,
        'newAddress.receiver_name': userInfo.real_name || userInfo.nickname || '',
        'newAddress.receiver_phone': userInfo.phone || ''
      });
    }
  },

  // 加载地址列表
  loadAddresses() {
    const token = wx.getStorageSync('token');
    console.log('加载地址列表, token:', token ? '存在' : '不存在');

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

    this.setData({
      loading: true
    });

    wx.request({
      url: api.userAddresses,
      method: 'GET',
      header: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      success: (res) => {
        console.log('地址列表响应:', res);
        if (res.statusCode === 200 && res.data.code === 200) {
          const addresses = res.data.data.map(addr => {
            // 创建用于显示的字符串
            const region_display = [addr.province, addr.city, addr.district].filter(item => item).join(' ');

            return {
              ...addr,
              region_display: region_display
            };
          });

          console.log('格式化后的地址:', addresses);

          this.setData({
            addresses: addresses,
            loading: false
          });
        } else {
          console.error('获取地址失败:', res.data);
          wx.showToast({
            title: res.data.message || '获取地址失败',
            icon: 'none'
          });
          this.setData({
            loading: false
          });
        }
      },
      fail: (err) => {
        console.error('加载地址失败:', err);
        wx.showToast({
          title: '网络错误',
          icon: 'none'
        });
        this.setData({
          loading: false
        });
      }
    });
  },

  // 打开添加地址弹窗
  onAddAddressClick() {
    console.log('打开添加地址弹窗');
    const userInfo = wx.getStorageSync('userInfo');

    // 重置表单数据
    this.setData({
      showAddDialog: true,
      editMode: false,
      currentAddressId: null,
      newAddress: {
        receiver_name: userInfo?.real_name || userInfo?.nickname || '',
        receiver_phone: userInfo?.phone || '',
        country: '中国',
        province: '',
        city: '',
        district: '',
        detail_address: '',
        postal_code: '',
        address_tag: 'home',
        is_default: false
      },
      region: [] // 重置region数组
    });
  },

  // 处理地区选择
  handleRegionChange(e) {
    const selectedRegion = e.detail.value;
    console.log('选择的地区:', selectedRegion);

    // 确保selectedRegion是数组
    if (!Array.isArray(selectedRegion)) {
      console.error('地区选择器返回的不是数组:', selectedRegion);
      return;
    }

    // 更新region数组
    this.setData({
      region: selectedRegion
    });

    // 延迟更新newAddress中的数据，确保视图已更新
    setTimeout(() => {
      this.setData({
        'newAddress.province': selectedRegion[0] || '',
        'newAddress.city': selectedRegion[1] || '',
        'newAddress.district': selectedRegion[2] || ''
      });
    }, 50);
  },

  // 处理输入
  handleInput(e) {
    const {
      field
    } = e.currentTarget.dataset;
    const value = e.detail.value;
    console.log('输入字段:', field, '值:', value);

    this.setData({
      [`newAddress.${field}`]: value
    });
  },

  // 选择标签
  handleTagSelect(e) {
    const tag = e.currentTarget.dataset.tag;
    console.log('选择标签:', tag);

    this.setData({
      'newAddress.address_tag': tag
    });
  },

  // 设为默认切换
  handleDefaultChange(e) {
    console.log('设置默认地址:', e.detail.value);

    this.setData({
      'newAddress.is_default': e.detail.value
    });
  },

  // 验证表单
  validateForm() {
    const {
      receiver_name,
      receiver_phone,
      province,
      city,
      district,
      detail_address
    } = this.data.newAddress;

    console.log('验证表单数据:', {
      receiver_name,
      receiver_phone,
      province,
      city,
      district,
      detail_address
    });

    if (!receiver_name || receiver_name.trim() === '') {
      wx.showToast({
        title: '请输入收货人姓名',
        icon: 'none'
      });
      return false;
    }

    if (!receiver_phone || receiver_phone.trim() === '') {
      wx.showToast({
        title: '请输入联系电话',
        icon: 'none'
      });
      return false;
    }

    // 简单的手机号验证
    const phoneRegex = /^1[3-9]\d{9}$/;
    if (!phoneRegex.test(receiver_phone)) {
      wx.showToast({
        title: '请输入正确的手机号',
        icon: 'none'
      });
      return false;
    }

    if (!province || !city || !district) {
      wx.showToast({
        title: '请选择完整的省市区',
        icon: 'none'
      });
      return false;
    }

    if (!detail_address || detail_address.trim() === '') {
      wx.showToast({
        title: '请输入详细地址',
        icon: 'none'
      });
      return false;
    }

    return true;
  },

  // 保存地址
  onSaveAddress() {
    console.log('保存地址，模式:', this.data.editMode ? '编辑' : '添加');
    console.log('当前地区选择:', this.data.region);
    console.log('当前地址数据:', this.data.newAddress);

    // 确保地区数据已同步
    if (this.data.region && this.data.region.length === 3) {
      this.setData({
        'newAddress.province': this.data.region[0] || '',
        'newAddress.city': this.data.region[1] || '',
        'newAddress.district': this.data.region[2] || ''
      }, () => {
        // 数据更新后验证并提交
        setTimeout(() => {
          this.submitAddress();
        }, 100);
      });
    } else {
      this.submitAddress();
    }
  },

  // 提交地址
  submitAddress() {
    if (!this.validateForm()) {
      return;
    }

    const addressData = {
      ...this.data.newAddress
    };

    // 移除空字符串
    Object.keys(addressData).forEach(key => {
      if (addressData[key] === '') {
        addressData[key] = null;
      }
    });

    console.log('保存地址数据:', addressData);

    if (this.data.editMode && this.data.currentAddressId) {
      this.updateAddress(this.data.currentAddressId, addressData);
    } else {
      this.createAddress(addressData);
    }
  },

  // 创建地址
  createAddress(addressData) {
    const token = wx.getStorageSync('token');
    if (!token) {
      wx.showToast({
        title: '请先登录',
        icon: 'none'
      });
      return;
    }

    console.log('创建地址请求数据:', addressData);

    wx.showLoading({
      title: '创建中...',
      mask: true
    });

    wx.request({
      url: api.userAddresses,
      method: 'POST',
      header: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      data: addressData,
      success: (res) => {
        wx.hideLoading();
        console.log('创建地址响应:', res);

        if (res.statusCode === 201 || res.statusCode === 200) {
          // 检查响应格式
          let success = false;
          if (res.data && res.data.code) {
            success = res.data.code === 201 || res.data.code === 200;
          } else {
            // 假设创建成功
            success = true;
          }

          if (success) {
            wx.showToast({
              title: '地址创建成功',
              icon: 'success'
            });
            this.setData({
              showAddDialog: false
            });
            this.loadAddresses(); // 刷新列表
          } else {
            wx.showToast({
              title: res.data.message || '创建失败',
              icon: 'none'
            });
          }
        } else {
          let errorMsg = '创建失败';
          if (res.data) {
            if (typeof res.data === 'object') {
              errorMsg = res.data.message || JSON.stringify(res.data);
            } else {
              errorMsg = res.data;
            }
          }
          wx.showToast({
            title: errorMsg,
            icon: 'none'
          });
        }
      },
      fail: (err) => {
        wx.hideLoading();
        console.error('创建地址失败:', err);
        wx.showToast({
          title: '网络错误',
          icon: 'none'
        });
      }
    });
  },

  // 更新地址
  updateAddress(id, addressData) {
    const token = wx.getStorageSync('token');
    if (!token) {
      wx.showToast({
        title: '请先登录',
        icon: 'none'
      });
      return;
    }

    console.log('更新地址请求数据:', addressData);

    wx.showLoading({
      title: '更新中...',
      mask: true
    });

    wx.request({
      url: `${api.userAddresses}${id}/`,
      method: 'PUT',
      header: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      data: addressData,
      success: (res) => {
        wx.hideLoading();
        console.log('更新地址响应:', res);

        if (res.statusCode === 200) {
          if (res.data && res.data.code === 200) {
            wx.showToast({
              title: '地址更新成功',
              icon: 'success'
            });
            this.setData({
              showAddDialog: false
            });
            this.loadAddresses(); // 刷新列表
          } else {
            wx.showToast({
              title: res.data.message || '更新失败',
              icon: 'none'
            });
          }
        } else {
          wx.showToast({
            title: `更新失败: ${res.statusCode}`,
            icon: 'none'
          });
        }
      },
      fail: (err) => {
        wx.hideLoading();
        console.error('更新地址失败:', err);
        wx.showToast({
          title: '网络错误',
          icon: 'none'
        });
      }
    });
  },

  // 编辑地址
  editAddress(e) {
    const id = e.currentTarget.dataset.id;
    const address = this.data.addresses.find(item => item.id === id);

    console.log('编辑地址:', id, address);

    if (address) {
      // 创建region数组用于picker组件
      const regionArray = [];

      if (address.province) {
        regionArray.push(address.province);
      } else {
        regionArray.push('');
      }

      if (address.city) {
        regionArray.push(address.city);
      } else {
        regionArray.push('');
      }

      if (address.district) {
        regionArray.push(address.district);
      } else {
        regionArray.push('');
      }

      console.log('设置的region数组:', regionArray);

      this.setData({
        showAddDialog: true,
        editMode: true,
        currentAddressId: id,
        newAddress: {
          receiver_name: address.receiver_name,
          receiver_phone: address.receiver_phone,
          country: address.country || '中国',
          province: address.province || '',
          city: address.city || '',
          district: address.district || '',
          detail_address: address.detail_address || '',
          postal_code: address.postal_code || '',
          address_tag: address.address_tag || 'home',
          is_default: address.is_default || false
        },
        region: regionArray
      });
    }
  },

  // 设为默认地址
  setAsDefault(e) {
    const id = e.currentTarget.dataset.id;
    console.log('设为默认地址:', id);

    const token = wx.getStorageSync('token');
    if (!token) {
      wx.showToast({
        title: '请先登录',
        icon: 'none'
      });
      return;
    }

    wx.showLoading({
      title: '设置中...',
      mask: true
    });

    wx.request({
      url: `${api.userAddresses}${id}/set_default/`,
      method: 'POST',
      header: {
        'Authorization': `Bearer ${token}`
      },
      success: (res) => {
        wx.hideLoading();
        console.log('设置默认地址响应:', res);

        if (res.statusCode === 200 && res.data && res.data.code === 200) {
          wx.showToast({
            title: '设置默认地址成功',
            icon: 'success'
          });
          this.loadAddresses(); // 刷新列表
        } else {
          wx.showToast({
            title: res.data ? res.data.message : '设置失败',
            icon: 'none'
          });
        }
      },
      fail: (err) => {
        wx.hideLoading();
        console.error('设置默认地址失败:', err);
        wx.showToast({
          title: '网络错误',
          icon: 'none'
        });
      }
    });
  },

  // 删除地址
  deleteAddress(e) {
    const id = e.currentTarget.dataset.id;
    console.log('删除地址:', id);

    wx.showModal({
      title: '确认删除',
      content: '确定要删除这个地址吗？',
      success: (res) => {
        if (res.confirm) {
          const token = wx.getStorageSync('token');
          if (!token) {
            wx.showToast({
              title: '请先登录',
              icon: 'none'
            });
            return;
          }

          wx.showLoading({
            title: '删除中...',
            mask: true
          });

          wx.request({
            url: `${api.userAddresses}${id}/`,
            method: 'DELETE',
            header: {
              'Authorization': `Bearer ${token}`
            },
            success: (res) => {
              wx.hideLoading();
              console.log('删除地址响应:', res);

              if (res.statusCode === 200 || res.statusCode === 204) {
                wx.showToast({
                  title: '地址删除成功',
                  icon: 'success'
                });
                this.loadAddresses(); // 刷新列表
              } else {
                wx.showToast({
                  title: '删除失败',
                  icon: 'none'
                });
              }
            },
            fail: (err) => {
              wx.hideLoading();
              console.error('删除地址失败:', err);
              wx.showToast({
                title: '网络错误',
                icon: 'none'
              });
            }
          });
        }
      }
    });
  },

  // 选择地图位置
  chooseLocation() {
    console.log('选择地图位置');
    wx.chooseLocation({
      success: (res) => {
        if (res) {
          console.log('选择的位置信息:', res);

          // 解析地址信息 
          const regionInfo = this.parseLocationData(res);
          console.log('解析的地区信息:', regionInfo);

          // 构建详细地址
          let detailAddress = this.buildDetailAddress(res);

          // 构建region数组
          const regionArray = [
            regionInfo.province || '',
            regionInfo.city || '',
            regionInfo.district || ''
          ];

          console.log('设置的region数组:', regionArray);

          // 使用延迟确保数据正确设置
          setTimeout(() => {
            this.setData({
              region: regionArray,
              'newAddress.province': regionInfo.province || '',
              'newAddress.city': regionInfo.city || '',
              'newAddress.district': regionInfo.district || '',
              'newAddress.detail_address': detailAddress
            }, () => {
              console.log('地图位置选择后数据已更新');
              console.log('当前region:', this.data.region);
              console.log('当前newAddress:', this.data.newAddress);

              wx.showToast({
                title: '位置已选择',
                icon: 'success'
              });
            });
          }, 100);
        }
      },
      fail: (err) => {
        console.error('选择位置失败:', err);
        if (err.errMsg.includes('auth deny')) {
          wx.showToast({
            title: '需要位置权限',
            icon: 'none'
          });
        }
      }
    });
  },

  // 位置数据解析方法
  parseLocationData(locationData) {
    console.log('解析位置数据:', locationData);

    const result = {
      province: '',
      city: '',
      district: ''
    };

    if (!locationData) {
      return result;
    }

    // 优先使用wx.chooseLocation返回的地区信息
    if (locationData.province) {
      result.province = locationData.province;
    }

    if (locationData.city) {
      result.city = locationData.city;
    }

    if (locationData.district) {
      result.district = locationData.district;
    }

    // 如果API没有返回地区信息，尝试从地址字符串解析
    if ((!result.province || !result.city || !result.district) && locationData.address) {
      const address = locationData.address;
      console.log('从地址字符串解析:', address);

      // 尝试多种解析方式
      const parsedRegion = this.parseAddressString(address);
      if (parsedRegion.province && !result.province) {
        result.province = parsedRegion.province;
      }
      if (parsedRegion.city && !result.city) {
        result.city = parsedRegion.city;
      }
      if (parsedRegion.district && !result.district) {
        result.district = parsedRegion.district;
      }
    }

    console.log('最终解析结果:', result);
    return result;
  },

  // 从地址字符串解析省市区
  parseAddressString(address) {
    const result = {
      province: '',
      city: '',
      district: ''
    };

    if (!address) return result;

    // 常见地区后缀
    const provinceSuffix = ['省', '自治区'];
    const citySuffix = ['市', '州', '地区', '盟'];
    const districtSuffix = ['区', '县', '旗', '市'];

    let remaining = address;

    // 解析省份
    for (const suffix of provinceSuffix) {
      const index = remaining.indexOf(suffix);
      if (index !== -1) {
        result.province = remaining.substring(0, index + 1);
        remaining = remaining.substring(index + 1);
        break;
      }
    }

    // 如果没有匹配到省份后缀，尝试查找直辖市
    if (!result.province) {
      const municipalities = ['北京市', '天津市', '上海市', '重庆市'];
      for (const municipality of municipalities) {
        if (address.startsWith(municipality)) {
          result.province = municipality;
          result.city = municipality;
          remaining = address.substring(municipality.length);
          break;
        }
      }
    }

    // 解析城市
    for (const suffix of citySuffix) {
      const index = remaining.indexOf(suffix);
      if (index !== -1) {
        result.city = remaining.substring(0, index + 1);
        remaining = remaining.substring(index + 1);
        break;
      }
    }

    // 解析区县
    for (const suffix of districtSuffix) {
      const index = remaining.indexOf(suffix);
      if (index !== -1 && index < 10) { // 限制在前10个字符内查找
        result.district = remaining.substring(0, index + 1);
        break;
      }
    }

    return result;
  },

  // 构建详细地址
  buildDetailAddress(locationData) {
    let detailAddress = '';

    if (locationData.name && locationData.address) {
      // 如果地址中已包含名称，则只显示地址
      if (locationData.address.includes(locationData.name)) {
        detailAddress = locationData.address;
      } else {
        detailAddress = `${locationData.name} (${locationData.address})`;
      }
    } else if (locationData.name) {
      detailAddress = locationData.name;
    } else if (locationData.address) {
      detailAddress = locationData.address;
    }

    return detailAddress;
  },

  // 处理地区选择 
  handleRegionChange(e) {
    const selectedRegion = e.detail.value;
    console.log('选择的地区:', selectedRegion);

    // 确保selectedRegion是数组且长度为3
    if (!Array.isArray(selectedRegion) || selectedRegion.length !== 3) {
      console.error('地区选择器返回的数据格式不正确:', selectedRegion);
      return;
    }

    // 检查是否有空值
    const hasEmpty = selectedRegion.some(item => !item || item.trim() === '');
    if (hasEmpty) {
      console.warn('地区选择包含空值:', selectedRegion);
    }

    // 更新region数组
    this.setData({
      region: selectedRegion
    });

    // 使用延迟确保数据更新
    setTimeout(() => {
      this.setData({
        'newAddress.province': selectedRegion[0] || '',
        'newAddress.city': selectedRegion[1] || '',
        'newAddress.district': selectedRegion[2] || ''
      }, () => {
        console.log('地区选择后数据已更新');
        console.log('当前region:', this.data.region);
        console.log('当前newAddress:', this.data.newAddress);
      });
    }, 50);
  },

  // 取消添加/编辑
  onCancelAdd() {
    console.log('取消添加/编辑');
    this.setData({
      showAddDialog: false,
      editMode: false,
      currentAddressId: null
    });
  }
});