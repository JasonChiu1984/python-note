# Cython `.so` 打包範例

這是一個最小可跑的 Cython extension 範例，展示 `.pyx -> .c -> .so` 的本機開發流程。

## 專案結構

```text
cython_so_example/
  pyproject.toml
  setup.py
  src/fastmath/__init__.py
  src/fastmath/_core.pyx
  demo.py
```

## 建置

```bash
python -m pip install -U Cython setuptools wheel
python setup.py build_ext --inplace
```

macOS / Linux 會在 `src/fastmath/` 產生類似：

```text
_core.cpython-311-darwin.so
_core.cpython-311-x86_64-linux-gnu.so
```

Windows 對應副檔名通常是 `.pyd`。

## 驗收

```bash
python demo.py
python -c "from fastmath import add_range; print(add_range(100))"
ls src/fastmath/*_core*.so
```

預期輸出：

```text
add_range(100) = 5050
weighted_sum([1, 2, 3], 0.5) = 3.0
5050
src/fastmath/_core.cpython-311-darwin.so
```

## 工程提醒

- `.so` 是平台相關 binary，不應假設可跨 OS 或 CPU 架構共用。
- 發佈給其他人時，建議用 `python -m build` 產生 wheel，並在目標平台安裝後 smoke test。
- `build_ext --inplace` 適合本機開發，不等於正式 release。
