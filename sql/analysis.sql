-- =====================================================================
-- Delivery Ops Analytics — SQL analysis (SQLite)
-- Database: data/processed/deliveries.db   Table: deliveries
-- "Late" = delivery took more than 30 minutes (our SLA for this analysis)
-- Run a single query:  sqlite3 data/processed/deliveries.db < sql/analysis.sql
-- =====================================================================


-- Q1. Headline KPIs
SELECT
    COUNT(*)                                              AS total_orders,
    COUNT(DISTINCT partner_id)                            AS partners,
    COUNT(DISTINCT city_name)                             AS cities,
    ROUND(AVG(delivery_min), 1)                           AS avg_delivery_min,
    ROUND(100.0 * AVG(delivery_min > 30), 1)              AS late_pct,
    ROUND(AVG(partner_rating), 2)                         AS avg_partner_rating
FROM deliveries;


-- Q2. How much does traffic slow us down?
SELECT
    traffic,
    COUNT(*)                                  AS orders,
    ROUND(AVG(delivery_min), 1)               AS avg_delivery_min,
    ROUND(100.0 * AVG(delivery_min > 30), 1)  AS late_pct
FROM deliveries
WHERE traffic IS NOT NULL
GROUP BY traffic
ORDER BY avg_delivery_min;


-- Q3. Weather impact
SELECT
    weather,
    COUNT(*)                                  AS orders,
    ROUND(AVG(delivery_min), 1)               AS avg_delivery_min,
    ROUND(100.0 * AVG(delivery_min > 30), 1)  AS late_pct
FROM deliveries
WHERE weather IS NOT NULL
GROUP BY weather
ORDER BY avg_delivery_min DESC;


-- Q4. When do orders come in, and when are they slowest? (time slot x traffic)
SELECT
    time_slot,
    traffic,
    COUNT(*)                     AS orders,
    ROUND(AVG(delivery_min), 1)  AS avg_delivery_min
FROM deliveries
WHERE time_slot IS NOT NULL AND traffic IS NOT NULL
GROUP BY time_slot, traffic
ORDER BY time_slot, avg_delivery_min;


-- Q5. Does stacking orders on one partner (multiple deliveries) hurt speed?
SELECT
    CAST(multiple_deliveries AS INT)          AS extra_orders_carried,
    COUNT(*)                                  AS orders,
    ROUND(AVG(delivery_min), 1)               AS avg_delivery_min,
    ROUND(100.0 * AVG(delivery_min > 30), 1)  AS late_pct
FROM deliveries
WHERE multiple_deliveries IS NOT NULL
GROUP BY extra_orders_carried
ORDER BY extra_orders_carried;


-- Q6. Festival days vs normal days
SELECT
    festival,
    COUNT(*)                                  AS orders,
    ROUND(AVG(delivery_min), 1)               AS avg_delivery_min,
    ROUND(100.0 * AVG(delivery_min > 30), 1)  AS late_pct
FROM deliveries
WHERE festival IS NOT NULL
GROUP BY festival;


-- Q7. City league table — which cities need attention?
SELECT
    city_name,
    COUNT(*)                                  AS orders,
    ROUND(AVG(delivery_min), 1)               AS avg_delivery_min,
    ROUND(100.0 * AVG(delivery_min > 30), 1)  AS late_pct,
    RANK() OVER (ORDER BY AVG(delivery_min > 30) DESC) AS late_rank
FROM deliveries
GROUP BY city_name
ORDER BY late_pct DESC;


-- Q8. Partner rating vs delivery speed
SELECT
    CASE
        WHEN partner_rating < 4.0 THEN 'a) below 4.0'
        WHEN partner_rating < 4.5 THEN 'b) 4.0-4.4'
        WHEN partner_rating < 4.8 THEN 'c) 4.5-4.7'
        ELSE                           'd) 4.8-5.0'
    END                                       AS rating_band,
    COUNT(*)                                  AS orders,
    ROUND(AVG(delivery_min), 1)               AS avg_delivery_min,
    ROUND(100.0 * AVG(delivery_min > 30), 1)  AS late_pct
FROM deliveries
WHERE partner_rating IS NOT NULL
GROUP BY rating_band
ORDER BY rating_band;


-- Q9. Vehicle condition (0 = best, 3 = worst)
SELECT
    vehicle_condition,
    COUNT(*)                                  AS orders,
    ROUND(AVG(delivery_min), 1)               AS avg_delivery_min,
    ROUND(100.0 * AVG(delivery_min > 30), 1)  AS late_pct
FROM deliveries
GROUP BY vehicle_condition
ORDER BY vehicle_condition;


-- Q10. Distance bands
SELECT
    CASE
        WHEN distance_km < 5  THEN 'a) under 5 km'
        WHEN distance_km < 10 THEN 'b) 5-10 km'
        WHEN distance_km < 15 THEN 'c) 10-15 km'
        ELSE                       'd) 15+ km'
    END                                       AS distance_band,
    COUNT(*)                                  AS orders,
    ROUND(AVG(delivery_min), 1)               AS avg_delivery_min,
    ROUND(100.0 * AVG(delivery_min > 30), 1)  AS late_pct
FROM deliveries
WHERE distance_km IS NOT NULL
GROUP BY distance_band
ORDER BY distance_band;


-- Q11. Partners who are late most often (min. 20 orders) — coaching list
WITH partner_stats AS (
    SELECT
        partner_id,
        city_name,
        COUNT(*)                                  AS orders,
        ROUND(AVG(delivery_min), 1)               AS avg_delivery_min,
        ROUND(100.0 * AVG(delivery_min > 30), 1)  AS late_pct,
        ROUND(AVG(partner_rating), 2)             AS rating
    FROM deliveries
    GROUP BY partner_id, city_name
    HAVING COUNT(*) >= 20
)
SELECT *
FROM partner_stats
ORDER BY late_pct DESC
LIMIT 10;
