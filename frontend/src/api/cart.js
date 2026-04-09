import request from '../utils/request'

export const cartApi = {
  // Get cart items
  getCart() {
    return request.get('/cart/')
  },

  // Add to cart
  addToCart(productId, quantity = 1) {
    return request.post('/cart/add/', { product_id: productId, quantity })
  },

  // Update quantity
  updateQuantity(cartItemId, quantity) {
    return request.post('/cart/update_quantity/', { cart_item_id: cartItemId, quantity })
  },

  // Remove from cart
  removeFromCart(cartItemId) {
    return request.post('/cart/remove/', { cart_item_id: cartItemId })
  },

  // Clear cart
  clearCart() {
    return request.post('/cart/clear/')
  }
}
