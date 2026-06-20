"""Store POS - Main Application"""
import os
import sys
from datetime import datetime, date, timedelta
from flask import Flask, render_template, request, jsonify, Response

# Ensure we can import models
sys.path.insert(0, os.path.dirname(__file__))
from models import get_db, init_db

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False


# ─── Initialize ────────────────────────────────────────────────
@app.before_request
def ensure_db():
    init_db()


# ─── Pages ─────────────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/products')
def products_page():
    return render_template('products.html')


@app.route('/orders')
def orders_page():
    return render_template('orders.html')


@app.route('/stats')
def stats_page():
    return render_template('stats.html')


@app.route('/weekly')
def weekly_page():
    return render_template('weekly.html')


# ─── API: Products ─────────────────────────────────────────────
@app.route('/api/products', methods=['GET'])
def list_products():
    search = request.args.get('search', '').strip()
    conn = get_db()
    if search:
        rows = conn.execute(
            "SELECT * FROM products WHERE name LIKE ? ORDER BY id DESC",
            (f'%{search}%',)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM products ORDER BY id DESC"
        ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route('/api/products', methods=['POST'])
def add_product():
    data = request.get_json(force=True)
    name = data.get('name', '').strip()
    if not name:
        return jsonify({'error': '商品名称不能为空'}), 400
    try:
        price = float(data.get('price', 0))
        stock = int(data.get('stock', 0))
        discount = int(data.get('discount', 0))
        if discount < 0 or discount > 100:
            return jsonify({'error': '折扣范围 0-100'}), 400
    except (ValueError, TypeError):
        return jsonify({'error': '价格或库存格式错误'}), 400
    category = data.get('category', '').strip()
    conn = get_db()
    conn.execute(
        "INSERT INTO products (name, price, category, stock, discount) VALUES (?,?,?,?,?)",
        (name, price, category, stock, discount)
    )
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


@app.route('/api/products/<int:pid>', methods=['PUT'])
def update_product(pid):
    data = request.get_json(force=True)
    name = data.get('name', '').strip()
    if not name:
        return jsonify({'error': '商品名称不能为空'}), 400
    try:
        price = float(data.get('price', 0))
        stock = int(data.get('stock', 0))
        discount = int(data.get('discount', 0))
        if discount < 0 or discount > 100:
            return jsonify({'error': '折扣范围 0-100'}), 400
    except (ValueError, TypeError):
        return jsonify({'error': '价格或库存格式错误'}), 400
    category = data.get('category', '').strip()
    conn = get_db()
    conn.execute(
        "UPDATE products SET name=?, price=?, category=?, stock=?, discount=? WHERE id=?",
        (name, price, category, stock, discount, pid)
    )
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


@app.route('/api/products/<int:pid>', methods=['DELETE'])
def delete_product(pid):
    conn = get_db()
    conn.execute("DELETE FROM products WHERE id=?", (pid,))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


# ─── API: Orders ───────────────────────────────────────────────
@app.route('/api/orders', methods=['POST'])
def create_order():
    """Create an order (checkout). Body: {items: [{product_id, quantity}], note: ''}"""
    data = request.get_json(force=True)
    items = data.get('items', [])
    note = data.get('note', '').strip()
    if not items:
        return jsonify({'error': '订单为空'}), 400

    conn = get_db()
    total = 0.0
    total_qty = 0
    order_items = []

    for item in items:
        pid = item.get('product_id')
        qty = int(item.get('quantity', 1))
        if qty <= 0:
            continue
        row = conn.execute(
            "SELECT * FROM products WHERE id=?", (pid,)
        ).fetchone()
        if not row:
            continue
        # Check stock
        if row['stock'] < qty:
            conn.close()
            return jsonify({'error': f'{row["name"]} 库存不足（剩余 {row["stock"]}）'}), 400

        # Apply discount if any
        unit_price = row['price']
        discount = row['discount'] or 0
        if discount > 0:
            unit_price = round(unit_price * (100 - discount) / 100, 2)

        subtotal = round(unit_price * qty, 2)
        total += subtotal
        total_qty += qty
        order_items.append({
            'product_id': pid,
            'product_name': row['name'],
            'quantity': qty,
            'unit_price': unit_price,
            'subtotal': subtotal
        })
        # Decrement stock
        conn.execute(
            "UPDATE products SET stock=stock-? WHERE id=?",
            (qty, pid)
        )

    if not order_items:
        conn.close()
        return jsonify({'error': '未找到有效商品'}), 400

    total = round(total, 2)
    cur = conn.execute(
        "INSERT INTO orders (total_amount, item_count, note) VALUES (?,?,?)",
        (total, total_qty, note)
    )
    order_id = cur.lastrowid

    for oi in order_items:
        conn.execute(
            "INSERT INTO order_items (order_id, product_id, product_name, quantity, unit_price, subtotal) VALUES (?,?,?,?,?,?)",
            (order_id, oi['product_id'], oi['product_name'],
             oi['quantity'], oi['unit_price'], oi['subtotal'])
        )

    conn.commit()
    conn.close()
    return jsonify({'ok': True, 'order_id': order_id, 'total': total})


@app.route('/api/orders', methods=['GET'])
def list_orders():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    offset = (page - 1) * per_page
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM orders ORDER BY id DESC LIMIT ? OFFSET ?",
        (per_page, offset)
    ).fetchall()
    total = conn.execute("SELECT COUNT(*) as c FROM orders").fetchone()['c']
    conn.close()
    return jsonify({
        'orders': [dict(r) for r in rows],
        'total': total,
        'page': page,
        'pages': (total + per_page - 1) // per_page
    })


@app.route('/api/orders/<int:oid>', methods=['GET'])
def get_order(oid):
    conn = get_db()
    order = conn.execute("SELECT * FROM orders WHERE id=?", (oid,)).fetchone()
    if not order:
        conn.close()
        return jsonify({'error': '订单不存在'}), 404
    items = conn.execute(
        "SELECT * FROM order_items WHERE order_id=?", (oid,)
    ).fetchall()
    conn.close()
    return jsonify({
        'order': dict(order),
        'items': [dict(i) for i in items]
    })


@app.route('/api/orders/<int:oid>/refund', methods=['POST'])
def refund_order(oid):
    conn = get_db()
    order = conn.execute(
        "SELECT * FROM orders WHERE id=? AND status='completed'",
        (oid,)
    ).fetchone()
    if not order:
        conn.close()
        return jsonify({'error': '订单不存在或已退款'}), 400
    # Restore stock
    items = conn.execute(
        "SELECT * FROM order_items WHERE order_id=?", (oid,)
    ).fetchall()
    for item in items:
        if item['product_id']:
            conn.execute(
                "UPDATE products SET stock=stock+? WHERE id=?",
                (item['quantity'], item['product_id'])
            )
    conn.execute(
        "UPDATE orders SET status='refunded' WHERE id=?",
        (oid,)
    )
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


@app.route('/api/orders/<int:oid>', methods=['PUT'])
def update_order(oid):
    """Edit an order: update note."""
    data = request.get_json(force=True)
    note = data.get('note', '').strip()
    conn = get_db()
    order = conn.execute("SELECT * FROM orders WHERE id=?", (oid,)).fetchone()
    if not order:
        conn.close()
        return jsonify({'error': '订单不存在'}), 404
    conn.execute("UPDATE orders SET note=? WHERE id=?", (note, oid))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


@app.route('/api/orders/<int:oid>', methods=['DELETE'])
def delete_order(oid):
    """Hard delete an order permanently."""
    conn = get_db()
    order = conn.execute("SELECT * FROM orders WHERE id=?", (oid,)).fetchone()
    if not order:
        conn.close()
        return jsonify({'error': '订单不存在'}), 404
    # Restore stock if completed
    if order['status'] == 'completed':
        items = conn.execute(
            "SELECT * FROM order_items WHERE order_id=?", (oid,)
        ).fetchall()
        for item in items:
            if item['product_id']:
                conn.execute(
                    "UPDATE products SET stock=stock+? WHERE id=?",
                    (item['quantity'], item['product_id'])
                )
    # Delete order (cascade deletes order_items)
    conn.execute("DELETE FROM orders WHERE id=?", (oid,))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


# ─── API: Stats ────────────────────────────────────────────────
@app.route('/api/stats/today')
def stats_today():
    today = date.today().isoformat()
    conn = get_db()
    row = conn.execute(
        "SELECT COUNT(*) as order_count, COALESCE(SUM(total_amount),0) as revenue, "
        "COALESCE(SUM(item_count),0) as items_sold "
        "FROM orders WHERE date(created_at)=? AND status='completed'",
        (today,)
    ).fetchone()

    # Top products today
    top = conn.execute("""
        SELECT oi.product_name, SUM(oi.quantity) as qty, SUM(oi.subtotal) as total
        FROM order_items oi
        JOIN orders o ON o.id = oi.order_id
        WHERE date(o.created_at)=? AND o.status='completed'
        GROUP BY oi.product_id ORDER BY qty DESC LIMIT 5
    """, (today,)).fetchall()

    # Recent orders today
    recent = conn.execute("""
        SELECT id, total_amount, item_count, created_at
        FROM orders WHERE date(created_at)=?
        ORDER BY id DESC LIMIT 10
    """, (today,)).fetchall()

    conn.close()
    return jsonify({
        'date': today,
        'order_count': row['order_count'],
        'revenue': round(row['revenue'], 2),
        'items_sold': row['items_sold'],
        'top_products': [dict(t) for t in top],
        'recent_orders': [dict(r) for r in recent]
    })


@app.route('/api/stats/weekly')
def stats_weekly():
    """Weekly stats: daily breakdown + order details"""
    # Determine current week (Mon-Sun)
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    week_start = monday.isoformat()
    week_end = sunday.isoformat()

    conn = get_db()

    # Daily breakdown
    daily = conn.execute("""
        SELECT date(created_at) as day,
               COUNT(*) as order_count,
               COALESCE(SUM(total_amount),0) as revenue,
               COALESCE(SUM(item_count),0) as items_sold
        FROM orders
        WHERE date(created_at) BETWEEN ? AND ?
          AND status='completed'
        GROUP BY date(created_at)
        ORDER BY day
    """, (week_start, week_end)).fetchall()

    # Fill in days with zero
    daily_map = {r['day']: dict(r) for r in daily}
    week_days = []
    total_revenue = 0
    total_orders = 0
    total_items = 0
    for i in range(7):
        d = (monday + timedelta(days=i)).isoformat()
        if d in daily_map:
            day_data = daily_map[d]
            total_revenue += day_data['revenue']
            total_orders += day_data['order_count']
            total_items += day_data['items_sold']
        else:
            day_data = {'day': d, 'order_count': 0, 'revenue': 0, 'items_sold': 0}
        week_days.append(day_data)

    # All completed orders this week with items
    orders_raw = conn.execute("""
        SELECT id, total_amount, item_count, note, created_at
        FROM orders
        WHERE date(created_at) BETWEEN ? AND ?
          AND status='completed'
        ORDER BY created_at DESC
    """, (week_start, week_end)).fetchall()

    order_list = []
    for o in orders_raw:
        items = conn.execute(
            "SELECT product_name, quantity, unit_price, subtotal FROM order_items WHERE order_id=?",
            (o['id'],)
        ).fetchall()
        order_list.append({
            'id': o['id'],
            'total_amount': o['total_amount'],
            'item_count': o['item_count'],
            'created_at': o['created_at'],
            'items': [dict(i) for i in items]
        })

    # Time-of-day distribution (by hour)
    hour_dist = conn.execute("""
        SELECT CAST(strftime('%H', created_at) AS INTEGER) as hour,
               COUNT(*) as count,
               COALESCE(SUM(total_amount),0) as revenue
        FROM orders
        WHERE date(created_at) BETWEEN ? AND ?
          AND status='completed'
        GROUP BY hour
        ORDER BY hour
    """, (week_start, week_end)).fetchall()

    conn.close()

    # Day names
    day_names_cn = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']

    return jsonify({
        'week_start': week_start,
        'week_end': week_end,
        'total_revenue': round(total_revenue, 2),
        'total_orders': total_orders,
        'total_items': total_items,
        'daily': week_days,
        'day_names': day_names_cn,
        'orders': order_list,
        'hour_distribution': [dict(h) for h in hour_dist]
    })


# ─── Seed Demo Data ────────────────────────────────────────────
@app.route('/api/seed')
def seed_demo():
    """Insert demo products and sample orders for testing."""
    conn = get_db()

    # Skip if already seeded
    existing = conn.execute("SELECT COUNT(*) as c FROM products").fetchone()['c']
    if existing > 0:
        conn.close()
        return jsonify({'ok': True, 'message': '已有数据，跳过'})

    demo_products = [
        ('美式咖啡', 22, '饮品', 100, 0),
        ('拿铁咖啡', 28, '饮品', 80, 0),
        ('卡布奇诺', 26, '饮品', 60, 0),
        ('抹茶拿铁', 32, '饮品', 40, 0),
        ('芒果冰沙', 35, '饮品', 30, 0),
        ('提拉米苏', 38, '甜品', 15, 0),
        ('芝士蛋糕', 35, '甜品', 20, 10),
        ('巧克力松饼', 18, '甜品', 25, 0),
        ('牛角包', 15, '面包', 30, 0),
        ('三明治', 28, '轻食', 20, 0),
    ]
    for name, price, cat, stock, disc in demo_products:
        conn.execute(
            "INSERT INTO products (name, price, category, stock, discount) VALUES (?,?,?,?,?)",
            (name, price, cat, stock, disc)
        )

    # Create sample orders across this week
    from datetime import datetime, timedelta
    import random
    today = date.today()
    monday = today - timedelta(days=today.weekday())

    for day_offset in range(7):
        day_date = monday + timedelta(days=day_offset)
        # Skip future days
        if day_date > today:
            continue

        order_count = random.randint(1, 5)
        for _ in range(order_count):
            hour = random.randint(8, 20)
            minute = random.randint(0, 59)
            ts = datetime(
                day_date.year, day_date.month, day_date.day,
                hour, minute
            ).strftime('%Y-%m-%d %H:%M:%S')

            # Pick 1-3 random products
            products = conn.execute(
                "SELECT id, name, price, stock FROM products ORDER BY RANDOM() LIMIT ?",
                (random.randint(1, 3),)
            ).fetchall()

            total = 0
            total_qty = 0
            items_data = []
            for p in products:
                qty = random.randint(1, 2)
                sub = round(p['price'] * qty, 2)
                total += sub
                total_qty += qty
                items_data.append({
                    'product_id': p['id'],
                    'product_name': p['name'],
                    'quantity': qty,
                    'unit_price': p['price'],
                    'subtotal': sub
                })

            total = round(total, 2)
            sample_notes = ['少糖', '多冰', '打包', '堂食', '', '', '']
            note = random.choice(sample_notes)
            cur = conn.execute(
                "INSERT INTO orders (total_amount, item_count, note, created_at) VALUES (?,?,?,?)",
                (total, total_qty, note, ts)
            )
            oid = cur.lastrowid
            for it in items_data:
                conn.execute(
                    "INSERT INTO order_items (order_id, product_id, product_name, quantity, unit_price, subtotal) VALUES (?,?,?,?,?,?)",
                    (oid, it['product_id'], it['product_name'],
                     it['quantity'], it['unit_price'], it['subtotal'])
                )

    conn.commit()
    conn.close()
    return jsonify({'ok': True, 'message': '示例数据已生成！'})


# ─── CSV Export ────────────────────────────────────────────────
def csv_response(filename, headers, rows):
    """Build a CSV response for download."""
    import io, csv
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    writer.writerows(rows)
    return Response(
        output.getvalue(),
        mimetype='text/csv; charset=utf-8-sig',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )


@app.route('/api/export/products.csv')
def export_products_csv():
    conn = get_db()
    rows = conn.execute("SELECT id, name, price, category, stock, discount, created_at FROM products ORDER BY id").fetchall()
    conn.close()
    return csv_response('products.csv',
        ['ID','商品名称','价格','分类','库存','折扣%','创建时间'],
        [[r['id'],r['name'],r['price'],r['category'],r['stock'],r['discount'],r['created_at']] for r in rows])


@app.route('/api/export/orders.csv')
def export_orders_csv():
    conn = get_db()
    rows = conn.execute("""
        SELECT o.id, o.total_amount, o.item_count, o.status, o.created_at,
               oi.product_name, oi.quantity, oi.unit_price, oi.subtotal
        FROM orders o LEFT JOIN order_items oi ON oi.order_id = o.id
        ORDER BY o.id DESC, oi.id
    """).fetchall()
    conn.close()
    return csv_response('orders.csv',
        ['订单ID','总金额','总件数','状态','下单时间','商品名','数量','单价','小计'],
        [[r['id'],r['total_amount'],r['item_count'],
          '已完成' if r['status']=='completed' else '已退款',
          r['created_at'],r['product_name'],r['quantity'],r['unit_price'],r['subtotal']] for r in rows])


@app.route('/api/export/weekly.csv')
def export_weekly_csv():
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    conn = get_db()
    rows = conn.execute("""
        SELECT o.id, o.total_amount, o.item_count, o.created_at,
               oi.product_name, oi.quantity, oi.unit_price, oi.subtotal
        FROM orders o LEFT JOIN order_items oi ON oi.order_id = o.id
        WHERE date(o.created_at) BETWEEN ? AND date(?, '+6 days')
          AND o.status='completed'
        ORDER BY o.created_at DESC, oi.id
    """, (monday.isoformat(), monday.isoformat())).fetchall()
    conn.close()
    return csv_response(f'weekly_{monday.isoformat()}.csv',
        ['订单ID','总金额','总件数','下单时间','商品名','数量','单价','小计'],
        [[r['id'],r['total_amount'],r['item_count'],
          r['created_at'],r['product_name'],r['quantity'],r['unit_price'],r['subtotal']] for r in rows])


# ─── Product Options ───────────────────────────────────────────
@app.route('/api/products/<int:pid>/options', methods=['GET'])
def list_product_options(pid):
    conn = get_db()
    rows = conn.execute("SELECT id, group_name, option_name, price_adjustment, sort_order FROM product_options WHERE product_id=? ORDER BY group_name, sort_order, id", (pid,)).fetchall()
    conn.close()
    groups = {}
    for r in rows:
        g = r['group_name']
        if g not in groups: groups[g] = []
        groups[g].append({'id': r['id'], 'option_name': r['option_name'], 'price_adjustment': r['price_adjustment'], 'sort_order': r['sort_order']})
    return jsonify([{'group_name': g, 'options': opts} for g, opts in groups.items()])


@app.route('/api/products/<int:pid>/options', methods=['POST'])
def save_product_options(pid):
    data = request.get_json(force=True)
    conn = get_db()
    conn.execute("DELETE FROM product_options WHERE product_id=?", (pid,))
    sort = 0
    for group in data:
        gname = group.get('group_name', '').strip()
        if not gname: continue
        for opt in group.get('options', []):
            oname = opt.get('option_name', '').strip()
            if not oname: continue
            conn.execute("INSERT INTO product_options (product_id, group_name, option_name, price_adjustment, sort_order) VALUES (?,?,?,?,?)",
                (pid, gname, oname, float(opt.get('price_adjustment', 0)), sort))
            sort += 1
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


# ─── Chart Export ──────────────────────────────────────────────
@app.route('/api/stats/weekly/chart.png')
def weekly_chart_png():
    import matplotlib; matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from io import BytesIO
    from datetime import date, timedelta
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    conn = get_db()
    rows = conn.execute("SELECT date(created_at) as d, SUM(total_amount) as rev, COUNT(*) as cnt FROM orders WHERE date(created_at) BETWEEN ? AND ? AND status='completed' GROUP BY d ORDER BY d",
        (monday.isoformat(), (monday+timedelta(days=6)).isoformat())).fetchall()
    conn.close()
    days_cn = ['周一','周二','周三','周四','周五','周六','周日']
    revs, cnts, labels = [], [], []
    for i in range(7):
        d = monday + timedelta(days=i)
        ds = d.isoformat()
        found = [r for r in rows if r['d'] == ds]
        rev = round(found[0]['rev'], 2) if found else 0
        cnt = found[0]['cnt'] if found else 0
        revs.append(rev); cnts.append(cnt)
        labels.append(f'{days_cn[i]}\n{d.month}/{d.day}')
    fig, ax = plt.subplots(figsize=(10, 5), dpi=120)
    bars = ax.bar(range(7), revs, color='#38a169', width=0.6, edgecolor='#2f855a', linewidth=1.2)
    if revs and max(revs) > 0:
        for bar, rev, cnt in zip(bars, revs, cnts):
            ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+max(revs)*0.02, f'¥{rev}\n{cnt}单', ha='center', va='bottom', fontsize=9)
    ax.set_xticks(range(7)); ax.set_xticklabels(labels, fontsize=10)
    ax.set_ylabel('营收 (¥)', fontsize=11)
    ax.set_title(f'本周每日营收 ({monday.isoformat()} — {(monday+timedelta(days=6)).isoformat()})', fontsize=13, fontweight='bold')
    ax.set_ylim(0, max(revs)*1.25 if revs and max(revs)>0 else 100)
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
    ax.grid(axis='y', alpha=0.3); fig.tight_layout()
    buf = BytesIO(); fig.savefig(buf, format='png'); plt.close(fig)
    buf.seek(0)
    return Response(buf.getvalue(), mimetype='image/png', headers={'Content-Disposition': 'inline; filename=weekly_revenue.png'})


if __name__ == '__main__':
    init_db()
    app.run(host='127.0.0.1', port=5000, debug=False)
