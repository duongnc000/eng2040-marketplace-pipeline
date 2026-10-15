-- Distinct SQL statements actually executed during this run.
-- On fresh setup, source INSERT statements are supplied in data/raw.sql;
-- they are not duplicated here. On reused setup the import is skipped.

PRAGMA temp_store=MEMORY;

SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;

SELECT COUNT(*) FROM "category_translation";

PRAGMA table_info("category_translation");

SELECT SUM("product_category_name" IS NULL), COUNT(DISTINCT "product_category_name") FROM "category_translation";

SELECT MIN("product_category_name"), MAX("product_category_name") FROM "category_translation";

SELECT SUM("product_category_name_english" IS NULL), COUNT(DISTINCT "product_category_name_english") FROM "category_translation";

SELECT MIN("product_category_name_english"), MAX("product_category_name_english") FROM "category_translation";

SELECT COUNT(*) FROM "customers";

PRAGMA table_info("customers");

SELECT SUM("customer_id" IS NULL), COUNT(DISTINCT "customer_id") FROM "customers";

SELECT MIN("customer_id"), MAX("customer_id") FROM "customers";

SELECT SUM("customer_unique_id" IS NULL), COUNT(DISTINCT "customer_unique_id") FROM "customers";

SELECT MIN("customer_unique_id"), MAX("customer_unique_id") FROM "customers";

SELECT SUM("customer_zip_code_prefix" IS NULL), COUNT(DISTINCT "customer_zip_code_prefix") FROM "customers";

SELECT MIN("customer_zip_code_prefix"), MAX("customer_zip_code_prefix") FROM "customers";

SELECT SUM("customer_city" IS NULL), COUNT(DISTINCT "customer_city") FROM "customers";

SELECT MIN("customer_city"), MAX("customer_city") FROM "customers";

SELECT SUM("customer_state" IS NULL), COUNT(DISTINCT "customer_state") FROM "customers";

SELECT MIN("customer_state"), MAX("customer_state") FROM "customers";

SELECT COUNT(*) FROM "order_items";

PRAGMA table_info("order_items");

SELECT SUM("order_id" IS NULL), COUNT(DISTINCT "order_id") FROM "order_items";

SELECT MIN("order_id"), MAX("order_id") FROM "order_items";

SELECT SUM("order_item_id" IS NULL), COUNT(DISTINCT "order_item_id") FROM "order_items";

SELECT MIN("order_item_id"), MAX("order_item_id") FROM "order_items";

SELECT SUM("product_id" IS NULL), COUNT(DISTINCT "product_id") FROM "order_items";

SELECT MIN("product_id"), MAX("product_id") FROM "order_items";

SELECT SUM("seller_id" IS NULL), COUNT(DISTINCT "seller_id") FROM "order_items";

SELECT MIN("seller_id"), MAX("seller_id") FROM "order_items";

SELECT SUM("shipping_limit_date" IS NULL), COUNT(DISTINCT "shipping_limit_date") FROM "order_items";

SELECT MIN("shipping_limit_date"), MAX("shipping_limit_date") FROM "order_items";

SELECT SUM("price" IS NULL), COUNT(DISTINCT "price") FROM "order_items";

SELECT MIN("price"), MAX("price") FROM "order_items";

SELECT SUM("freight_value" IS NULL), COUNT(DISTINCT "freight_value") FROM "order_items";

SELECT MIN("freight_value"), MAX("freight_value") FROM "order_items";

SELECT COUNT(*) FROM "order_payments";

PRAGMA table_info("order_payments");

SELECT SUM("order_id" IS NULL), COUNT(DISTINCT "order_id") FROM "order_payments";

SELECT MIN("order_id"), MAX("order_id") FROM "order_payments";

SELECT SUM("payment_sequential" IS NULL), COUNT(DISTINCT "payment_sequential") FROM "order_payments";

SELECT MIN("payment_sequential"), MAX("payment_sequential") FROM "order_payments";

SELECT SUM("payment_type" IS NULL), COUNT(DISTINCT "payment_type") FROM "order_payments";

SELECT MIN("payment_type"), MAX("payment_type") FROM "order_payments";

SELECT SUM("payment_installments" IS NULL), COUNT(DISTINCT "payment_installments") FROM "order_payments";

SELECT MIN("payment_installments"), MAX("payment_installments") FROM "order_payments";

SELECT SUM("payment_value" IS NULL), COUNT(DISTINCT "payment_value") FROM "order_payments";

SELECT MIN("payment_value"), MAX("payment_value") FROM "order_payments";

SELECT COUNT(*) FROM "order_reviews";

PRAGMA table_info("order_reviews");

SELECT SUM("review_id" IS NULL), COUNT(DISTINCT "review_id") FROM "order_reviews";

SELECT MIN("review_id"), MAX("review_id") FROM "order_reviews";

SELECT SUM("order_id" IS NULL), COUNT(DISTINCT "order_id") FROM "order_reviews";

SELECT MIN("order_id"), MAX("order_id") FROM "order_reviews";

SELECT SUM("review_score" IS NULL), COUNT(DISTINCT "review_score") FROM "order_reviews";

SELECT MIN("review_score"), MAX("review_score") FROM "order_reviews";

SELECT SUM("review_comment_title" IS NULL), COUNT(DISTINCT "review_comment_title") FROM "order_reviews";

SELECT MIN("review_comment_title"), MAX("review_comment_title") FROM "order_reviews";

SELECT SUM("review_comment_message" IS NULL), COUNT(DISTINCT "review_comment_message") FROM "order_reviews";

SELECT MIN("review_comment_message"), MAX("review_comment_message") FROM "order_reviews";

SELECT SUM("review_creation_date" IS NULL), COUNT(DISTINCT "review_creation_date") FROM "order_reviews";

SELECT MIN("review_creation_date"), MAX("review_creation_date") FROM "order_reviews";

SELECT SUM("review_answer_timestamp" IS NULL), COUNT(DISTINCT "review_answer_timestamp") FROM "order_reviews";

SELECT MIN("review_answer_timestamp"), MAX("review_answer_timestamp") FROM "order_reviews";

SELECT COUNT(*) FROM "orders";

PRAGMA table_info("orders");

SELECT SUM("order_id" IS NULL), COUNT(DISTINCT "order_id") FROM "orders";

SELECT MIN("order_id"), MAX("order_id") FROM "orders";

SELECT SUM("customer_id" IS NULL), COUNT(DISTINCT "customer_id") FROM "orders";

SELECT MIN("customer_id"), MAX("customer_id") FROM "orders";

SELECT SUM("order_status" IS NULL), COUNT(DISTINCT "order_status") FROM "orders";

SELECT MIN("order_status"), MAX("order_status") FROM "orders";

SELECT SUM("order_purchase_timestamp" IS NULL), COUNT(DISTINCT "order_purchase_timestamp") FROM "orders";

SELECT MIN("order_purchase_timestamp"), MAX("order_purchase_timestamp") FROM "orders";

SELECT SUM("order_approved_at" IS NULL), COUNT(DISTINCT "order_approved_at") FROM "orders";

SELECT MIN("order_approved_at"), MAX("order_approved_at") FROM "orders";

SELECT SUM("order_delivered_carrier_date" IS NULL), COUNT(DISTINCT "order_delivered_carrier_date") FROM "orders";

SELECT MIN("order_delivered_carrier_date"), MAX("order_delivered_carrier_date") FROM "orders";

SELECT SUM("order_delivered_customer_date" IS NULL), COUNT(DISTINCT "order_delivered_customer_date") FROM "orders";

SELECT MIN("order_delivered_customer_date"), MAX("order_delivered_customer_date") FROM "orders";

SELECT SUM("order_estimated_delivery_date" IS NULL), COUNT(DISTINCT "order_estimated_delivery_date") FROM "orders";

SELECT MIN("order_estimated_delivery_date"), MAX("order_estimated_delivery_date") FROM "orders";

SELECT COUNT(*) FROM "products";

PRAGMA table_info("products");

SELECT SUM("product_id" IS NULL), COUNT(DISTINCT "product_id") FROM "products";

SELECT MIN("product_id"), MAX("product_id") FROM "products";

SELECT SUM("product_category_name" IS NULL), COUNT(DISTINCT "product_category_name") FROM "products";

SELECT MIN("product_category_name"), MAX("product_category_name") FROM "products";

SELECT SUM("product_name_lenght" IS NULL), COUNT(DISTINCT "product_name_lenght") FROM "products";

SELECT MIN("product_name_lenght"), MAX("product_name_lenght") FROM "products";

SELECT SUM("product_description_lenght" IS NULL), COUNT(DISTINCT "product_description_lenght") FROM "products";

SELECT MIN("product_description_lenght"), MAX("product_description_lenght") FROM "products";

SELECT SUM("product_photos_qty" IS NULL), COUNT(DISTINCT "product_photos_qty") FROM "products";

SELECT MIN("product_photos_qty"), MAX("product_photos_qty") FROM "products";

SELECT SUM("product_weight_g" IS NULL), COUNT(DISTINCT "product_weight_g") FROM "products";

SELECT MIN("product_weight_g"), MAX("product_weight_g") FROM "products";

SELECT SUM("product_length_cm" IS NULL), COUNT(DISTINCT "product_length_cm") FROM "products";

SELECT MIN("product_length_cm"), MAX("product_length_cm") FROM "products";

SELECT SUM("product_height_cm" IS NULL), COUNT(DISTINCT "product_height_cm") FROM "products";

SELECT MIN("product_height_cm"), MAX("product_height_cm") FROM "products";

SELECT SUM("product_width_cm" IS NULL), COUNT(DISTINCT "product_width_cm") FROM "products";

SELECT MIN("product_width_cm"), MAX("product_width_cm") FROM "products";

SELECT COUNT(*) FROM "sellers";

PRAGMA table_info("sellers");

SELECT SUM("seller_id" IS NULL), COUNT(DISTINCT "seller_id") FROM "sellers";

SELECT MIN("seller_id"), MAX("seller_id") FROM "sellers";

SELECT SUM("seller_zip_code_prefix" IS NULL), COUNT(DISTINCT "seller_zip_code_prefix") FROM "sellers";

SELECT MIN("seller_zip_code_prefix"), MAX("seller_zip_code_prefix") FROM "sellers";

SELECT SUM("seller_city" IS NULL), COUNT(DISTINCT "seller_city") FROM "sellers";

SELECT MIN("seller_city"), MAX("seller_city") FROM "sellers";

SELECT SUM("seller_state" IS NULL), COUNT(DISTINCT "seller_state") FROM "sellers";

SELECT MIN("seller_state"), MAX("seller_state") FROM "sellers";

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
FROM orders o WHERE NOT EXISTS (SELECT 1 FROM order_reviews r WHERE r.order_id=o.order_id);

SELECT SUM(price), SUM(freight_value) FROM order_items;

SELECT SUM(payment_value), COUNT(*), SUM(payment_installments=0) FROM order_payments;

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
GROUP BY i.order_id;

SELECT o.*, c.customer_unique_id, c.customer_zip_code_prefix,
       c.customer_city, c.customer_state,
       CASE WHEN c.customer_id IS NULL THEN 1 ELSE 0 END AS customer_not_found
FROM orders AS o
LEFT JOIN customers AS c ON c.customer_id = o.customer_id
ORDER BY o.order_id;

SELECT COUNT(*) FROM orders;

SELECT COUNT(*) FROM order_items;

SELECT SUM(CASE WHEN price>=0 THEN price ELSE 0 END) FROM order_items;

SELECT SUM(CASE WHEN freight_value>=0 THEN freight_value ELSE 0 END) FROM order_items;

SELECT SUM(price) FROM order_items;

SELECT SUM(freight_value) FROM order_items;
