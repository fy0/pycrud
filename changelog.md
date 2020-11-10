
### 0.1.19 update 2020.11.10

* Added: `is_` and `is_not` for field

* Added: unary operator for values: `array_extend` `array_extend_distinct` `array_prune_distinct`


### 0.1.18 update 2020.11.10

* Fixed: update filled all default values

* Fixed: perm lost bug

* Fixed: try_bind fix


### 0.1.17 update 2020.11.10

* Added: try to add unary operator for values


### 0.1.16 update 2020.11.09

* Changed: default dumps function for crud object

* Fixed: allow_delete can be inherit now.


### 0.1.15 update 2020.11.09

* Added: memoryview supported for blob field

* Fixed: $select- fix


### 0.1.14 update 2020.11.09

* Fixed: $select- now works

* Fixed: prefix operator

* Fixed: contains_any operator


### 0.1.13 update 2020.11.06

* Fixed: contains operator


### 0.1.12 update 2020.11.06

* Fixed: update failed for array/json fields

* Fixed: solve_condition 500


### 0.1.11 update 2020.11.06

* Added: pydantic type `HexString`, read hex string, output bytes


### 0.1.10 update 2020.11.06

* Added: $order-by supported


### 0.1.9 update 2020.11.06

* Fixed: peewee execute_sql

* Fixed: QueryResultRow.to_dict() failed


### 0.1.8 update 2020.11.05

* Added: simple dsl

* Added: list with count


### 0.1.7 update 2020.11.03

* Fixed: operator: contains, in, notin

* Fixed: no insert return for psycopg2

* Fixed: incorrect placeholder for psycopg2 and peewee


#### 0.1.6 update 2020.11.02

* Added: tortoise supported

* Added: PostgreSQL array field supported

* Added: json field supported

* Fixed: insert blob failed

* Fixed: pydantic 1.7 supported

* Fixed: pydantic error not throw
