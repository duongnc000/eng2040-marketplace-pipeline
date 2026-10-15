"""SQL used by the loading and cleaning stages."""

BASE_SQL = """
SELECT o.*, c.customer_unique_id, c.customer_zip_code_prefix,
       c.customer_city, c.customer_state,
       CASE WHEN c.customer_id IS NULL THEN 1 ELSE 0 END AS customer_not_found
FROM orders AS o
LEFT JOIN customers AS c ON c.customer_id = o.customer_id
ORDER BY o.order_id
"""

ITEM_SQL = """
SELECT i.order_id,
       COUNT(*) AS item_count,
       COUNT(DISTINCT i.product_id) AS distinct_product_count,
       COUNT(DISTINCT i.seller_id) AS distinct_seller_count,
       SUM(i.price) AS raw_price_total,
       SUM(i.freight_value) AS raw_freight_total,
       SUM(CASE WHEN i.price >= 0 THEN i.price ELSE 0 END) AS valid_price_total,
       SUM(CASE WHEN i.freight_value >= 0 THEN i.freight_value ELSE 0 END) AS valid_freight_total,
       SUM(i.price IS NULL OR i.price < 0) AS bad_price_count,
       SUM(i.freight_value IS NULL OR i.freight_value < 0) AS bad_freight_count,
       SUM(p.product_id IS NULL) AS unmatched_product_count,
       SUM(s.seller_id IS NULL) AS unmatched_seller_count,
       COUNT(DISTINCT CASE WHEN p.product_category_name IS NOT NULL
                           THEN p.product_category_name END) AS category_count,
       AVG(CASE WHEN p.product_weight_g > 0 THEN p.product_weight_g END) AS avg_weight_g,
       AVG(CASE WHEN p.product_length_cm > 0 AND p.product_height_cm > 0
                     AND p.product_width_cm > 0
                THEN p.product_length_cm * p.product_height_cm * p.product_width_cm END)
           AS avg_volume_cm3,
       SUM(p.product_id IS NULL OR p.product_category_name IS NULL
           OR p.product_weight_g IS NULL OR p.product_weight_g <= 0
           OR p.product_length_cm IS NULL OR p.product_length_cm <= 0
           OR p.product_height_cm IS NULL OR p.product_height_cm <= 0
           OR p.product_width_cm IS NULL OR p.product_width_cm <= 0)
           AS optional_product_issue_count,
       COUNT(DISTINCT CASE WHEN TRIM(s.seller_state) <> ''
                           THEN UPPER(TRIM(s.seller_state)) END) AS seller_state_count,
       SUM(CASE WHEN UPPER(TRIM(s.seller_state)) = UPPER(TRIM(c.customer_state))
                THEN 1 ELSE 0 END) AS same_state_item_count
FROM order_items AS i
LEFT JOIN products AS p ON p.product_id = i.product_id
LEFT JOIN sellers AS s ON s.seller_id = i.seller_id
LEFT JOIN orders AS o ON o.order_id = i.order_id
LEFT JOIN customers AS c ON c.customer_id = o.customer_id
GROUP BY i.order_id
"""

RELATIONSHIP_SQL = """
SELECT 'orders_missing_customer' AS check_name, COUNT(*) AS value
FROM orders o LEFT JOIN customers c ON c.customer_id=o.customer_id
WHERE c.customer_id IS NULL
UNION ALL SELECT 'items_missing_order', COUNT(*)
FROM order_items i LEFT JOIN orders o ON o.order_id=i.order_id WHERE o.order_id IS NULL
UNION ALL SELECT 'items_missing_product', COUNT(*)
FROM order_items i LEFT JOIN products p ON p.product_id=i.product_id WHERE p.product_id IS NULL
UNION ALL SELECT 'items_missing_seller', COUNT(*)
FROM order_items i LEFT JOIN sellers s ON s.seller_id=i.seller_id WHERE s.seller_id IS NULL
UNION ALL SELECT 'payments_missing_order', COUNT(*)
FROM order_payments p LEFT JOIN orders o ON o.order_id=p.order_id WHERE o.order_id IS NULL
UNION ALL SELECT 'reviews_missing_order', COUNT(*)
FROM order_reviews r LEFT JOIN orders o ON o.order_id=r.order_id WHERE o.order_id IS NULL
UNION ALL SELECT 'products_missing_category_translation', COUNT(*)
FROM products p LEFT JOIN category_translation t
ON t.product_category_name=p.product_category_name
WHERE p.product_category_name IS NOT NULL AND t.product_category_name IS NULL
UNION ALL SELECT 'orders_without_items', COUNT(*)
FROM orders o WHERE NOT EXISTS (SELECT 1 FROM order_items i WHERE i.order_id=o.order_id)
UNION ALL SELECT 'orders_without_payments', COUNT(*)
FROM orders o WHERE NOT EXISTS (SELECT 1 FROM order_payments p WHERE p.order_id=o.order_id)
UNION ALL SELECT 'orders_without_reviews', COUNT(*)
FROM orders o WHERE NOT EXISTS (SELECT 1 FROM order_reviews r WHERE r.order_id=o.order_id)
"""
