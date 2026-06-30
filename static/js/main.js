const CART_KEY = "drip_cart";

const Cart = {
  get() {
    return JSON.parse(localStorage.getItem(CART_KEY) || "[]");
  },
  save(items) {
    localStorage.setItem(CART_KEY, JSON.stringify(items));
  },
  add(item) {
    const items = Cart.get();
    const existing = items.find(i => i.key === item.key);
    if (existing) {
      existing.qty += item.qty;
    } else {
      items.push(item);
    }
    Cart.save(items);
    Cart.renderBadge();
  },
  remove(key) {
    Cart.save(Cart.get().filter(i => i.key !== key));
    Cart.renderBadge();
  },
  updateQty(key, delta) {
    const items = Cart.get().map(i =>
      i.key === key ? { ...i, qty: Math.max(1, i.qty + delta) } : i
    );
    Cart.save(items);
    Cart.renderBadge();
  },
  clear() {
    localStorage.removeItem(CART_KEY);
    Cart.renderBadge();
  },
  count() {
    return Cart.get().reduce((s, i) => s + i.qty, 0);
  },
  total() {
    return Cart.get().reduce((s, i) => s + i.price * i.qty, 0);
  },
  renderBadge() {
    const badge = document.getElementById("cart-badge");
    if (!badge) return;
    const n = Cart.count();
    badge.textContent = n > 0 ? n : "";
    badge.style.display = n > 0 ? "flex" : "none";
  }
};

function showToast(msg) {
  const t = document.createElement("div");
  t.className = "toast";
  t.textContent = msg;
  document.body.appendChild(t);
  requestAnimationFrame(() => t.classList.add("toast--show"));
  setTimeout(() => {
    t.classList.remove("toast--show");
    setTimeout(() => t.remove(), 300);
  }, 2000);
}

document.addEventListener("DOMContentLoaded", () => Cart.renderBadge());

// Splash — show once per browser session
(function () {
  var splash = document.getElementById("splash");
  if (!splash || splash.style.display === "none") return;
  sessionStorage.setItem("splashSeen", "1");
  setTimeout(function () {
    splash.classList.add("splash--exit");
    splash.addEventListener("transitionend", function () { splash.remove(); }, { once: true });
  }, 2000);
}());
