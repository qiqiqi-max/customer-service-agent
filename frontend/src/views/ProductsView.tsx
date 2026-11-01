import { SUPPORT_FUNCTIONS } from "../data/workbench";
import type { Product } from "../types";

export function ProductsView(props: {
  products: Product[];
  selectedProducts: Set<string>;
  selectedFunctions: Set<string>;
  onToggleFunction: (key: string) => void;
  onToggleProduct: (name: string) => void;
}) {
  return (
    <div className="page">
      <section className="panel">
        <div className="panel-head">
          <div>
            <h2>商品货架</h2>
            <p>勾选的商品会作为接待时的商品范围</p>
          </div>
          <span className="badge accent">
            {props.selectedProducts.size}/{props.products.length}
          </span>
        </div>
        <div className="panel-body">
          {props.products.length ? (
            <div className="product-grid">
              {props.products.map((product) => {
                const selected = props.selectedProducts.has(product.name);
                return (
                  <label key={product.name} className={selected ? "product-card is-selected" : "product-card"}>
                    <div className="product-thumb">{product.name.slice(0, 1)}</div>
                    <div>
                      <strong>{product.name}</strong>
                      <p>{product.description}</p>
                    </div>
                    <input checked={selected} onChange={() => props.onToggleProduct(product.name)} type="checkbox" />
                  </label>
                );
              })}
            </div>
          ) : (
            <p className="empty">商品数据暂未载入。</p>
          )}
        </div>
      </section>

      <section className="panel">
        <div className="panel-head">
          <div>
            <h2>能力开关</h2>
            <p>控制助手在接待中可以调用的工具</p>
          </div>
          <span className="badge accent">{props.selectedFunctions.size}</span>
        </div>
        <div className="panel-body">
          <div className="toggle-list">
            {SUPPORT_FUNCTIONS.map((item) => (
              <label key={item.key} className="toggle-item">
                <input
                  checked={props.selectedFunctions.has(item.key)}
                  onChange={() => props.onToggleFunction(item.key)}
                  type="checkbox"
                />
                <span>
                  <strong>{item.label}</strong>
                  <small>{item.description}</small>
                </span>
              </label>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
