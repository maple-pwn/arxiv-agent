// 客户端收藏清单：localStorage 存储 arXiv ID
(function () {
    'use strict';

    var STORE_KEY = 'arxiv_cart_v1';

    function getCart() {
        try {
            var raw = JSON.parse(localStorage.getItem(STORE_KEY)) || [];
            return Array.isArray(raw) ? raw : [];
        } catch (e) {
            return [];
        }
    }

    function saveCart(cart) {
        localStorage.setItem(STORE_KEY, JSON.stringify(cart));
    }

    function render() {
        var cart = getCart();

        document.querySelectorAll('.cart-title-count').forEach(function (el) {
            el.textContent = String(cart.length);
        });

        var idsEl = document.querySelector('.cart-ids');
        if (idsEl) {
            idsEl.textContent = cart.join('\n');
        }

        document.querySelectorAll('.cart-toggle-btn').forEach(function (btn) {
            var id = btn.getAttribute('data-id');
            var inCart = cart.indexOf(id) !== -1;
            btn.classList.toggle('in-cart', inCart);
            btn.textContent = inCart ? '已收藏' : '加入收藏';
        });
    }

    function toggle(id) {
        var cart = getCart();
        var idx = cart.indexOf(id);
        if (idx !== -1) {
            cart.splice(idx, 1);
        } else {
            cart.push(id);
        }
        saveCart(cart);
        render();
    }

    function copyAll() {
        var ids = getCart().join('\n');
        if (!ids) {
            alert('收藏清单为空');
            return;
        }
        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(ids).then(function () {
                alert('已复制 ' + getCart().length + ' 个 Arxiv ID');
            });
        } else {
            // 兜底：临时 textarea 复制
            var ta = document.createElement('textarea');
            ta.value = ids;
            document.body.appendChild(ta);
            ta.select();
            document.execCommand('copy');
            document.body.removeChild(ta);
            alert('已复制 ' + getCart().length + ' 个 Arxiv ID');
        }
    }

    document.addEventListener('click', function (e) {
        var toggleBtn = e.target.closest('.cart-toggle-btn');
        if (toggleBtn) {
            toggle(toggleBtn.getAttribute('data-id'));
            return;
        }
        if (e.target.closest('.cart-copy-btn')) {
            copyAll();
            return;
        }
        if (e.target.closest('.cart-clear-btn')) {
            saveCart([]);
            render();
            return;
        }
    });

    render();
})();
