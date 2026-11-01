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
    <section className="page-grid">
      <div className="surface">
        <div className="section-head">
          <div>
            <span className="eyebrow">商品范围</span>
            <h2>商品货架</h2>
          </div>
          <span className="count-badge">{props.products.length}</span>
        </div>
        <div className="product-grid">
          {props.products.map((product) => (
            <label key={product.name} className="product-card">
              <input
                checked={props.selectedProducts.has(product.name)}
                onChange={() => props.onToggleProduct(product.name)}
                type="checkbox"
              />
              <div className="product-thumb">{product.name.slice(0, 1)}</div>
              <div>
                <strong>{product.name}</strong>
                <p>{product.description}</p>
              </div>
            </label>
          ))}
        </div>
      </div>
      <div className="surface">
        <div className="section-head">
          <div>
            <span className="eyebrow">知识范围</span>
            <h2>能力开关</h2>
          </div>
        </div>
        <div className="check-list spacious">
          {SUPPORT_FUNCTIONS.map((item) => (
            <label key={item.key} className="check-card">
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
  );
}
