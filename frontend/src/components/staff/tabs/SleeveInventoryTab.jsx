// src/components/staff/tabs/SleeveInventoryTab.jsx
import React, { useState, useEffect, useCallback } from "react";
import {
  getSleeveProducts,
  createSleeveProduct,
  updateSleeveProduct,
  deleteSleeveProduct,
  runSleeveMatching,
  getToOrderList,
  getToSleeveList,
  updateSleeveStatus,
} from "../../../api/client";

/**
 * Sleeve Inventory tab - Manage sleeve products, view to-order and ready-to-sleeve lists
 */
export function SleeveInventoryTab() {
  const [activeSection, setActiveSection] = useState("inventory");
  const [products, setProducts] = useState([]);
  const [toOrderList, setToOrderList] = useState([]);
  const [toSleeveList, setToSleeveList] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  // Add product form
  const [showAddForm, setShowAddForm] = useState(false);
  const [addForm, setAddForm] = useState({
    distributor: "",
    item_id: "",
    name: "",
    width_mm: "",
    height_mm: "",
    sleeves_per_pack: "",
    price: "",
    in_stock: "0",
    ordered: "0",
  });

  // Inline editing
  const [editingId, setEditingId] = useState(null);
  const [editForm, setEditForm] = useState({});

  const showMessage = useCallback((msg, type = "success") => {
    if (type === "error") {
      setError(msg);
      setTimeout(() => setError(null), 5000);
    } else {
      setSuccess(msg);
      setTimeout(() => setSuccess(null), 3000);
    }
  }, []);

  // Load data based on active section
  useEffect(() => {
    if (activeSection === "inventory") loadProducts();
    else if (activeSection === "to-order") loadToOrder();
    else if (activeSection === "to-sleeve") loadToSleeve();
  }, [activeSection]);

  const loadProducts = async () => {
    setLoading(true);
    try {
      const data = await getSleeveProducts();
      setProducts(data);
    } catch (err) {
      showMessage("Failed to load products", "error");
    } finally {
      setLoading(false);
    }
  };

  const loadToOrder = async () => {
    setLoading(true);
    try {
      const data = await getToOrderList();
      setToOrderList(data);
    } catch (err) {
      showMessage("Failed to load to-order list", "error");
    } finally {
      setLoading(false);
    }
  };

  const loadToSleeve = async () => {
    setLoading(true);
    try {
      const data = await getToSleeveList();
      setToSleeveList(data);
    } catch (err) {
      showMessage("Failed to load ready-to-sleeve list", "error");
    } finally {
      setLoading(false);
    }
  };

  // ---- Product CRUD ----

  const handleAddProduct = async (e) => {
    e.preventDefault();
    try {
      await createSleeveProduct({
        distributor: addForm.distributor,
        item_id: addForm.item_id || null,
        name: addForm.name,
        width_mm: parseInt(addForm.width_mm),
        height_mm: parseInt(addForm.height_mm),
        sleeves_per_pack: parseInt(addForm.sleeves_per_pack),
        price: parseFloat(addForm.price),
        in_stock: parseInt(addForm.in_stock) || 0,
        ordered: parseInt(addForm.ordered) || 0,
      });
      showMessage("Product added");
      setShowAddForm(false);
      setAddForm({ distributor: "", item_id: "", name: "", width_mm: "", height_mm: "", sleeves_per_pack: "", price: "", in_stock: "0", ordered: "0" });
      loadProducts();
    } catch (err) {
      showMessage("Failed to add product", "error");
    }
  };

  const startEdit = (product) => {
    setEditingId(product.id);
    setEditForm({
      in_stock: String(product.in_stock),
      ordered: String(product.ordered),
      price: String(product.price),
    });
  };

  const handleSaveEdit = async (productId) => {
    try {
      const update = {};
      if (editForm.in_stock !== undefined) update.in_stock = parseInt(editForm.in_stock);
      if (editForm.ordered !== undefined) update.ordered = parseInt(editForm.ordered);
      if (editForm.price !== undefined) update.price = parseFloat(editForm.price);
      await updateSleeveProduct(productId, update);
      setEditingId(null);
      showMessage("Product updated");
      loadProducts();
    } catch (err) {
      showMessage("Failed to update product", "error");
    }
  };

  const handleDeleteProduct = async (productId, productName) => {
    if (!window.confirm(`Delete "${productName}"? This will clear product links on matched sleeves.`)) return;
    try {
      await deleteSleeveProduct(productId);
      showMessage("Product deleted");
      loadProducts();
    } catch (err) {
      showMessage("Failed to delete product", "error");
    }
  };

  // ---- Matching ----

  const handleRunMatching = async () => {
    setLoading(true);
    try {
      const result = await runSleeveMatching();
      showMessage(`Matching complete: ${result.matched} matched, ${result.unmatched} unmatched out of ${result.total}`);
      // Refresh whichever section is active
      if (activeSection === "to-order") loadToOrder();
      else if (activeSection === "to-sleeve") loadToSleeve();
    } catch (err) {
      showMessage("Matching failed", "error");
    } finally {
      setLoading(false);
    }
  };

  // ---- Mark ready sleeves as sleeved ----

  const handleSleeveReady = async (game) => {
    const readySleeves = game.sleeves.filter((s) => s.ready);
    const results = { success: 0, failed: 0 };
    for (const sleeve of readySleeves) {
      try {
        await updateSleeveStatus(sleeve.sleeve_id, true);
        results.success++;
      } catch (err) {
        results.failed++;
      }
    }
    if (results.failed > 0) {
      showMessage(
        `${results.success} sleeved, ${results.failed} failed (insufficient stock?)`,
        "error"
      );
    } else {
      const label = game.all_ready ? "fully" : `partially (${results.success}/${game.total_count})`;
      showMessage(`"${game.game_title}" ${label} sleeved`);
    }
    loadToSleeve();
  };

  // ---- CSV Export for to-order ----

  const handleExportToOrderCSV = () => {
    const rows = [["Size (mm)", "Total Needed", "Deficit", "Product", "Distributor", "Item ID", "Packs to Buy", "Price/Pack", "Total Cost", "Games"]];
    toOrderList.forEach((item) => {
      rows.push([
        `${item.width_mm}x${item.height_mm}`,
        item.total_needed,
        item.deficit,
        item.product?.product_name || "No match",
        item.product?.distributor || "",
        item.product?.item_id || "",
        item.product?.packs_to_buy || "",
        item.product?.price_per_pack || "",
        item.product?.total_cost || "",
        item.game_names.join("; "),
      ]);
    });
    const csv = rows.map((r) => r.join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "sleeve-order-list.csv";
    a.click();
    window.URL.revokeObjectURL(url);
  };

  const sections = [
    { id: "inventory", label: "Product Inventory" },
    { id: "to-sleeve", label: "Ready to Sleeve" },
    { id: "to-order", label: "To Order" },
  ];

  return (
    <div className="space-y-6">
      {/* Messages */}
      {error && (
        <div className="p-3 bg-red-50 border border-red-300 text-red-800 rounded-lg text-sm">
          {error}
        </div>
      )}
      {success && (
        <div className="p-3 bg-green-50 border border-green-300 text-green-800 rounded-lg text-sm">
          {success}
        </div>
      )}

      {/* Header with match button */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-xl font-bold">Sleeve Inventory</h2>
        <button
          onClick={handleRunMatching}
          disabled={loading}
          className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 text-sm font-medium"
        >
          {loading ? "Running..." : "Run Auto-Match"}
        </button>
      </div>

      {/* Sub-section tabs */}
      <div className="flex gap-1 border-b">
        {sections.map((s) => (
          <button
            key={s.id}
            onClick={() => setActiveSection(s.id)}
            className={`px-4 py-2 text-sm font-medium rounded-t-lg transition-colors ${
              activeSection === s.id
                ? "bg-white border border-b-white -mb-px text-purple-700"
                : "text-gray-500 hover:text-gray-700"
            }`}
          >
            {s.label}
          </button>
        ))}
      </div>

      {/* Section Content */}
      {activeSection === "inventory" && (
        <ProductInventorySection
          products={products}
          loading={loading}
          showAddForm={showAddForm}
          setShowAddForm={setShowAddForm}
          addForm={addForm}
          setAddForm={setAddForm}
          handleAddProduct={handleAddProduct}
          editingId={editingId}
          editForm={editForm}
          setEditForm={setEditForm}
          startEdit={startEdit}
          handleSaveEdit={handleSaveEdit}
          handleDeleteProduct={handleDeleteProduct}
          setEditingId={setEditingId}
        />
      )}
      {activeSection === "to-sleeve" && (
        <ReadyToSleeveSection
          list={toSleeveList}
          loading={loading}
          onSleeveReady={handleSleeveReady}
        />
      )}
      {activeSection === "to-order" && (
        <ToOrderSection
          list={toOrderList}
          loading={loading}
          onExportCSV={handleExportToOrderCSV}
        />
      )}
    </div>
  );
}

// ============================================================================
// Sub-sections
// ============================================================================

function ProductInventorySection({
  products, loading, showAddForm, setShowAddForm,
  addForm, setAddForm, handleAddProduct,
  editingId, editForm, setEditForm, startEdit, handleSaveEdit, handleDeleteProduct, setEditingId,
}) {
  if (loading) return <div className="text-center py-8 text-gray-500">Loading products...</div>;

  return (
    <div className="space-y-4">
      {/* Add button */}
      <div className="flex justify-end">
        <button
          onClick={() => setShowAddForm(!showAddForm)}
          className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 text-sm font-medium"
        >
          {showAddForm ? "Cancel" : "+ Add Product"}
        </button>
      </div>

      {/* Add form */}
      {showAddForm && (
        <form onSubmit={handleAddProduct} className="p-4 bg-gray-50 rounded-lg border space-y-3">
          <h3 className="font-semibold text-sm uppercase text-gray-600">New Sleeve Product</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <input placeholder="Distributor *" required value={addForm.distributor} onChange={(e) => setAddForm({ ...addForm, distributor: e.target.value })} className="border rounded px-3 py-2 text-sm" />
            <input placeholder="Item ID / SKU" value={addForm.item_id} onChange={(e) => setAddForm({ ...addForm, item_id: e.target.value })} className="border rounded px-3 py-2 text-sm" />
            <input placeholder="Product Name *" required value={addForm.name} onChange={(e) => setAddForm({ ...addForm, name: e.target.value })} className="border rounded px-3 py-2 text-sm col-span-2" />
            <input placeholder="Width (mm) *" required type="number" min="1" value={addForm.width_mm} onChange={(e) => setAddForm({ ...addForm, width_mm: e.target.value })} className="border rounded px-3 py-2 text-sm" />
            <input placeholder="Height (mm) *" required type="number" min="1" value={addForm.height_mm} onChange={(e) => setAddForm({ ...addForm, height_mm: e.target.value })} className="border rounded px-3 py-2 text-sm" />
            <input placeholder="Sleeves/Pack *" required type="number" min="1" value={addForm.sleeves_per_pack} onChange={(e) => setAddForm({ ...addForm, sleeves_per_pack: e.target.value })} className="border rounded px-3 py-2 text-sm" />
            <input placeholder="Price/Pack *" required type="number" step="0.01" min="0" value={addForm.price} onChange={(e) => setAddForm({ ...addForm, price: e.target.value })} className="border rounded px-3 py-2 text-sm" />
            <input placeholder="In Stock (sleeves)" type="number" min="0" value={addForm.in_stock} onChange={(e) => setAddForm({ ...addForm, in_stock: e.target.value })} className="border rounded px-3 py-2 text-sm" />
            <input placeholder="Ordered (packs)" type="number" min="0" value={addForm.ordered} onChange={(e) => setAddForm({ ...addForm, ordered: e.target.value })} className="border rounded px-3 py-2 text-sm" />
          </div>
          <button type="submit" className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 text-sm font-medium">
            Add Product
          </button>
        </form>
      )}

      {/* Products table */}
      {products.length === 0 ? (
        <div className="text-center py-8 text-gray-500">
          No sleeve products added yet. Add your first product above.
        </div>
      ) : (
        <div className="overflow-x-auto border rounded-lg">
          <table className="w-full text-sm">
            <thead className="bg-gray-100 border-b">
              <tr>
                <th className="px-3 py-2 text-left font-semibold">Distributor</th>
                <th className="px-3 py-2 text-left font-semibold">SKU</th>
                <th className="px-3 py-2 text-left font-semibold">Name</th>
                <th className="px-3 py-2 text-center font-semibold">Size (mm)</th>
                <th className="px-3 py-2 text-right font-semibold">Per Pack</th>
                <th className="px-3 py-2 text-right font-semibold">Price</th>
                <th className="px-3 py-2 text-right font-semibold">In Stock</th>
                <th className="px-3 py-2 text-right font-semibold">Ordered</th>
                <th className="px-3 py-2 text-center font-semibold">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {products.map((p) => (
                <tr key={p.id} className="hover:bg-gray-50">
                  <td className="px-3 py-2">{p.distributor}</td>
                  <td className="px-3 py-2 font-mono text-xs">{p.item_id || "—"}</td>
                  <td className="px-3 py-2 font-medium">{p.name}</td>
                  <td className="px-3 py-2 text-center font-mono">{p.width_mm} x {p.height_mm}</td>
                  <td className="px-3 py-2 text-right">{p.sleeves_per_pack}</td>

                  {editingId === p.id ? (
                    <>
                      <td className="px-3 py-2 text-right">
                        <input type="number" step="0.01" value={editForm.price} onChange={(e) => setEditForm({ ...editForm, price: e.target.value })} className="w-20 border rounded px-1 py-0.5 text-right text-sm" />
                      </td>
                      <td className="px-3 py-2 text-right">
                        <input type="number" value={editForm.in_stock} onChange={(e) => setEditForm({ ...editForm, in_stock: e.target.value })} className="w-20 border rounded px-1 py-0.5 text-right text-sm" />
                      </td>
                      <td className="px-3 py-2 text-right">
                        <input type="number" value={editForm.ordered} onChange={(e) => setEditForm({ ...editForm, ordered: e.target.value })} className="w-20 border rounded px-1 py-0.5 text-right text-sm" />
                        <div className="text-xs text-gray-400">= {parseInt(editForm.ordered || 0) * p.sleeves_per_pack} sleeves</div>
                      </td>
                      <td className="px-3 py-2 text-center space-x-1">
                        <button onClick={() => handleSaveEdit(p.id)} className="px-2 py-1 bg-green-600 text-white rounded text-xs hover:bg-green-700">Save</button>
                        <button onClick={() => setEditingId(null)} className="px-2 py-1 bg-gray-300 rounded text-xs hover:bg-gray-400">Cancel</button>
                      </td>
                    </>
                  ) : (
                    <>
                      <td className="px-3 py-2 text-right">${p.price.toFixed(2)}</td>
                      <td className="px-3 py-2 text-right">
                        <span className={p.in_stock > 0 ? "text-green-700 font-semibold" : "text-gray-400"}>
                          {p.in_stock}
                        </span>
                      </td>
                      <td className="px-3 py-2 text-right">
                        {p.ordered > 0 ? (
                          <span className="text-blue-600">{p.ordered} pks ({p.ordered_sleeves})</span>
                        ) : (
                          <span className="text-gray-400">—</span>
                        )}
                      </td>
                      <td className="px-3 py-2 text-center space-x-1">
                        <button onClick={() => startEdit(p)} className="px-2 py-1 bg-blue-100 text-blue-700 rounded text-xs hover:bg-blue-200">Edit</button>
                        <button onClick={() => handleDeleteProduct(p.id, p.name)} className="px-2 py-1 bg-red-100 text-red-700 rounded text-xs hover:bg-red-200">Del</button>
                      </td>
                    </>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Summary */}
      {products.length > 0 && (
        <div className="p-3 bg-gray-50 rounded-lg text-sm text-gray-600">
          <strong>{products.length}</strong> products | <strong>{products.reduce((sum, p) => sum + p.in_stock, 0)}</strong> total sleeves in stock
        </div>
      )}
    </div>
  );
}


function ReadyToSleeveSection({ list, loading, onSleeveReady }) {
  if (loading) return <div className="text-center py-8 text-gray-500">Loading...</div>;

  if (list.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        No games have sleevable requirements in stock. Either stock is insufficient or matching hasn't been run.
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <p className="text-sm text-gray-600">
        Games with at least one sleeve requirement covered by stock. Sleeve what you can now.
      </p>

      {list.map((game) => (
        <div key={game.game_id} className={`border rounded-lg p-4 bg-white hover:shadow-sm transition-shadow ${game.all_ready ? "border-green-300" : ""}`}>
          <div className="flex items-center justify-between mb-3">
            <div>
              <h3 className="font-semibold text-lg">{game.game_title}</h3>
              <span className={`text-xs ${game.all_ready ? "text-green-600" : "text-amber-600"}`}>
                {game.all_ready
                  ? "All sleeves ready"
                  : `${game.ready_count} of ${game.total_count} sleeve types ready`}
              </span>
            </div>
            <button
              onClick={() => onSleeveReady(game)}
              className={`px-3 py-1.5 text-white rounded-lg text-sm font-medium ${
                game.all_ready
                  ? "bg-green-600 hover:bg-green-700"
                  : "bg-amber-600 hover:bg-amber-700"
              }`}
            >
              {game.all_ready ? "Mark All Sleeved" : `Mark ${game.ready_count} of ${game.total_count} Sleeved`}
            </button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm table-auto">
              <thead>
                <tr className="text-left text-gray-500 text-xs uppercase border-b border-gray-200">
                  <th className="px-3 py-2">Status</th>
                  <th className="px-3 py-2">Card Type</th>
                  <th className="px-3 py-2">Size</th>
                  <th className="px-3 py-2 text-right">Qty</th>
                  <th className="px-3 py-2">Matched Product</th>
                  <th className="px-3 py-2 text-right">Stock</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {game.sleeves.map((s, i) => (
                  <tr key={i} className={s.ready ? "" : "opacity-50"}>
                    <td className="px-3 py-2">
                      {s.ready
                        ? <span className="text-green-600 font-semibold text-xs">READY</span>
                        : <span className="text-gray-400 text-xs">{s.product_name ? "Low stock" : "No match"}</span>
                      }
                    </td>
                    <td className="px-3 py-2">{s.card_name || "Standard Cards"}</td>
                    <td className="px-3 py-2 font-mono">{s.width_mm} x {s.height_mm}</td>
                    <td className="px-3 py-2 text-right">{s.quantity}</td>
                    <td className="px-3 py-2 text-purple-700">{s.product_name || "—"}</td>
                    <td className="px-3 py-2 text-right">
                      {s.product_stock != null ? (
                        <span className={s.ready ? "text-green-700" : "text-red-500"}>
                          {s.product_stock}
                        </span>
                      ) : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ))}
    </div>
  );
}


function ToOrderSection({ list, loading, onExportCSV }) {
  if (loading) return <div className="text-center py-8 text-gray-500">Loading...</div>;

  if (list.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        All sleeve requirements are covered by current stock and orders. Nothing to order.
      </div>
    );
  }

  const totalCost = list.reduce((sum, item) => sum + (item.product?.total_cost || 0), 0);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-600">
          Sleeve sizes where stock + orders are insufficient.
        </p>
        <button
          onClick={onExportCSV}
          className="px-3 py-1.5 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 text-sm"
        >
          Export CSV
        </button>
      </div>

      <div className="overflow-x-auto border rounded-lg">
        <table className="w-full text-sm">
          <thead className="bg-gray-100 border-b">
            <tr>
              <th className="px-3 py-2 text-left font-semibold">Size (mm)</th>
              <th className="px-3 py-2 text-right font-semibold">Needed</th>
              <th className="px-3 py-2 text-right font-semibold">Deficit</th>
              <th className="px-3 py-2 text-left font-semibold">Product</th>
              <th className="px-3 py-2 text-left font-semibold">Distributor</th>
              <th className="px-3 py-2 text-right font-semibold">Packs</th>
              <th className="px-3 py-2 text-right font-semibold">Cost</th>
              <th className="px-3 py-2 text-left font-semibold">Games</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {list.map((item, idx) => (
              <tr key={idx} className="hover:bg-gray-50">
                <td className="px-3 py-2 font-mono">{item.width_mm} x {item.height_mm}</td>
                <td className="px-3 py-2 text-right">{item.total_needed}</td>
                <td className="px-3 py-2 text-right font-semibold text-red-600">{item.deficit}</td>
                {item.product ? (
                  <>
                    <td className="px-3 py-2">{item.product.product_name}</td>
                    <td className="px-3 py-2">{item.product.distributor}</td>
                    <td className="px-3 py-2 text-right">{item.product.packs_to_buy}</td>
                    <td className="px-3 py-2 text-right">${item.product.total_cost.toFixed(2)}</td>
                  </>
                ) : (
                  <>
                    <td className="px-3 py-2 text-orange-600 italic" colSpan={3}>No matching product</td>
                  </>
                )}
                <td className="px-3 py-2 text-xs text-gray-600">{item.game_names.join(", ")}</td>
              </tr>
            ))}
          </tbody>
          <tfoot className="bg-gray-50 border-t font-semibold">
            <tr>
              <td colSpan={6} className="px-3 py-2 text-right">Total Estimated Cost:</td>
              <td className="px-3 py-2 text-right">${totalCost.toFixed(2)}</td>
              <td></td>
            </tr>
          </tfoot>
        </table>
      </div>

      <div className="p-3 bg-blue-50 rounded-lg text-sm text-blue-800">
        <strong>{list.length}</strong> sizes need ordering across <strong>{list.reduce((s, i) => s + i.games_count, 0)}</strong> game requirements
      </div>
    </div>
  );
}
