.PHONY: run seed clean archive

# ─── 店家端收费系统 - 常用命令 ───────────────────────────

## 启动服务（默认 5000 端口）
run:
	python3 app.py

## 启动服务（指定端口）
run-port:
	@read -p "端口号 (默认 5000): " port; \
	port=$${port:-5000}; \
	sed -i "s/port=[0-9]*/port=$$port/" app.py 2>/dev/null; \
	PYTHONPATH=. python3 app.py

## 生成示例数据（需要服务在运行）
seed:
	curl -s http://127.0.0.1:5000/api/seed | python3 -m json.tool

## 导出数据
export:
	@mkdir -p exports
	curl -s http://127.0.0.1:5000/api/export/products.csv -o exports/products.csv
	curl -s http://127.0.0.1:5000/api/export/orders.csv -o exports/orders.csv
	curl -s http://127.0.0.1:5000/api/export/weekly.csv -o exports/weekly.csv
	@echo "✅ 已导出到 exports/ 目录"

## 清理缓存和数据库（⚠️ 会删除所有数据！）
clean:
	rm -f store.db store.db-wal store.db-shm
	rm -rf __pycache__ */__pycache__
	rm -rf exports/
	@echo "✅ 已清理"

## 创建发布包
archive:
	@echo "创建发布包..."
	@cd .. && tar czf store-pos/store-pos-v1.0.0.tar.gz \
		--exclude='store.db*' \
		--exclude='__pycache__' \
		--exclude='.git' \
		--exclude='exports' \
		--transform='s|^store-pos|store-pos-v1.0.0|' \
		store-pos/
	@echo "✅ 已创建: store-pos-v1.0.0.tar.gz"
	@ls -lh store-pos-v1.0.0.tar.gz

## 显示帮助
help:
	@echo "可用命令:"
	@echo "  make run       — 启动服务"
	@echo "  make seed     — 生成示例数据"
	@echo "  make export   — 导出所有数据为 CSV"
	@echo "  make clean    — 清理缓存和数据库"
	@echo "  make archive  — 创建发布包"
