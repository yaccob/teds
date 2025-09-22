# TeDS Default Validation Report

## Table of Contents

- [Overview](#overview)
- [Executive Summary](#executive-summary)
- [Detailed Results](#detailed-results)
- [Appendix](#appendix)

## Overview

| Property | Value |
|----------|-------|
| Tool Version | teds 0.1.dev13+g9e84ef6db.d20250920 |
| Specification Support | 1.0-1.0 |
| Recommended Version | 1.0 |
| Generated | 2025-09-22T15:26:35.676231+02:00 |
| Report File | demo/sample_tests.yaml |







## Executive Summary
















































































This report analyzes **10** schema(s) with a total of **50** test cases.

### Results Summary

| Status | Count | Description |
|--------|-------|-------------|

| ✅ **SUCCESS** | 40 | Test cases passed as expected |


| ⚠️ **WARNING** | 3 | Test cases with warnings (review recommended) |


| ❌ **ERROR** | 7 | Test cases failed validation |


| **Total** | **50** | All test cases processed |





## Detailed Results




### sample_schemas.yaml#/components/schemas/Email <a id="sample-schemas-yaml--components-schemas-email"></a>





#### Schema Summary

| Metric | Count |
|--------|-------|
| Valid Cases | 3 |
| Invalid Cases | 1 |
| Total Cases | 4 |


#### Valid Test Cases


##### `.components.schemas.Email.examples[0]`

**Status:** ✅ SUCCESS

**Payload:**
```yaml
alice@example.com
```



---


##### `.components.schemas.Email.examples[1]`

**Status:** ⚠️ WARNING

**Payload:**
```yaml
not-an-email
```



---


##### `good email`

**Status:** ✅ SUCCESS

**Payload:**
```yaml
alice@example.com
```



---





#### Invalid Test Cases


##### `not an email`

**Status:** ❌ ERROR

**Payload:**
```yaml
not-an-email
```


**Message:** UNEXPECTEDLY VALID
A validator that *ignores* 'format' accepted this instance, while a strict validator (enforcing 'format') might reject it as desired (format: email).
Consider enforcing the expected format by adding an explicit 'pattern' property to the schema.


---








### sample_schemas.yaml#/components/schemas/User <a id="sample-schemas-yaml--components-schemas-user"></a>





#### Schema Summary

| Metric | Count |
|--------|-------|
| Valid Cases | 4 |
| Invalid Cases | 4 |
| Total Cases | 8 |


#### Valid Test Cases


##### `.components.schemas.User.examples[0]`

**Status:** ✅ SUCCESS

**Payload:**
```yaml
id: 3fa85f64-5717-4562-b3fc-2c963f66afa6
name: Alice Example
email: alice@example.com
```



---


##### `.components.schemas.User.examples[1]`

**Status:** ❌ ERROR

**Payload:**
```yaml
id: not-a-uuid
name: bob
email: x
```


**Message:** 'not-a-uuid' is not a 'uuid'


---


##### `minimal valid user`

**Status:** ✅ SUCCESS

**Payload:**
```yaml
id: 3fa85f64-5717-4562-b3fc-2c963f66afa6
name: Alice Example
email: alice@example.com
```



---


##### `parse as JSON string`

**Status:** ✅ SUCCESS

**Payload:**
```yaml
'{"id":"3fa85f64-5717-4562-b3fc-2c963f66afa6","name":"Bob Builder","email":"bob@example.com"}'
```



---





#### Invalid Test Cases


##### `missing required prop`

**Status:** ✅ SUCCESS

**Payload:**
```yaml
id: 3fa85f64-5717-4562-b3fc-2c963f66afa6
name: Alice Example
```


**Message:** 'email' is a required property


---


##### `additional property`

**Status:** ✅ SUCCESS

**Payload:**
```yaml
id: 3fa85f64-5717-4562-b3fc-2c963f66afa6
name: Alice Example
email: alice@example.com
extra: nope
```


**Message:** Additional properties are not allowed ('extra' was unexpected)


---


##### `bad uuid`

**Status:** ❌ ERROR

**Payload:**
```yaml
id: not-a-uuid
name: Alice Example
email: alice@example.com
```


**Message:** UNEXPECTEDLY VALID
A validator that *ignores* 'format' accepted this instance, while a strict validator (enforcing 'format') might reject it as desired (format: uuid).
Consider enforcing the expected format by adding an explicit 'pattern' property to the schema.


---


##### `bad name pattern`

**Status:** ✅ SUCCESS

**Payload:**
```yaml
id: 3fa85f64-5717-4562-b3fc-2c963f66afa6
name: alice example
email: alice@example.com
```


**Message:** 'alice example' does not match '^[A-Z][a-zA-Z]+(?: [A-Z][a-zA-Z]+)*$'


---








### sample_schemas.yaml#/components/schemas/Identifier <a id="sample-schemas-yaml--components-schemas-identifier"></a>





#### Schema Summary

| Metric | Count |
|--------|-------|
| Valid Cases | 4 |
| Invalid Cases | 2 |
| Total Cases | 6 |


#### Valid Test Cases


##### `.components.schemas.Identifier.examples[0]`

**Status:** ✅ SUCCESS

**Payload:**
```yaml
AB-123
```



---


##### `.components.schemas.Identifier.examples[1]`

**Status:** ✅ SUCCESS

**Payload:**
```yaml
99
```



---


##### `AB-777`

**Status:** ✅ SUCCESS

**Payload:**
```yaml
undefined
```



---


##### `forty-two`

**Status:** ✅ SUCCESS

**Payload:**
```yaml
42
```



---





#### Invalid Test Cases


##### `zero not allowed`

**Status:** ✅ SUCCESS

**Payload:**
```yaml
0
```


**Message:** 0 is not valid under any of the given schemas


---


##### `wrong string pattern`

**Status:** ✅ SUCCESS

**Payload:**
```yaml
A-1
```


**Message:** 'A-1' is not valid under any of the given schemas


---








### sample_schemas.yaml#/components/schemas/Color <a id="sample-schemas-yaml--components-schemas-color"></a>





#### Schema Summary

| Metric | Count |
|--------|-------|
| Valid Cases | 2 |
| Invalid Cases | 1 |
| Total Cases | 3 |


#### Valid Test Cases


##### `.components.schemas.Color.examples[0]`

**Status:** ✅ SUCCESS

**Payload:**
```yaml
green
```



---


##### `simple enum ok`

**Status:** ✅ SUCCESS

**Payload:**
```yaml
red
```



---





#### Invalid Test Cases


##### `not in enum`

**Status:** ✅ SUCCESS

**Payload:**
```yaml
yellow
```


**Message:** 'yellow' is not one of ['red', 'green', 'blue']


---








### sample_schemas.yaml#/components/schemas/Regexy <a id="sample-schemas-yaml--components-schemas-regexy"></a>





#### Schema Summary

| Metric | Count |
|--------|-------|
| Valid Cases | 2 |
| Invalid Cases | 1 |
| Total Cases | 3 |


#### Valid Test Cases


##### `.components.schemas.Regexy.examples[0]`

**Status:** ✅ SUCCESS

**Payload:**
```yaml
abc12
```



---


##### `regex ok`

**Status:** ✅ SUCCESS

**Payload:**
```yaml
abc12
```



---





#### Invalid Test Cases


##### `uppercase not allowed`

**Status:** ✅ SUCCESS

**Payload:**
```yaml
AB123
```


**Message:** 'AB123' does not match '^[a-z]{3}\\d{2}$'


---








### sample_schemas.yaml#/components/schemas/Product <a id="sample-schemas-yaml--components-schemas-product"></a>





#### Schema Summary

| Metric | Count |
|--------|-------|
| Valid Cases | 3 |
| Invalid Cases | 2 |
| Total Cases | 5 |


#### Valid Test Cases


##### `.components.schemas.Product.examples[0]`

**Status:** ✅ SUCCESS

**Payload:**
```yaml
sku: SKU1234
price: 12.5
tags:
- key: env
  value: prod
color: red
```



---


##### `full product`

**Status:** ✅ SUCCESS

**Payload:**
```yaml
sku: SKU1234
price: 12.5
tags:
- key: env
  value: prod
color: blue
```



---


##### `json string`

**Status:** ✅ SUCCESS

**Payload:**
```yaml
'{"sku":"SKU9999","price":0,"tags":[{"key":"env","value":"prod"}],"color":"green"}'
```



---





#### Invalid Test Cases


##### `negative price`

**Status:** ✅ SUCCESS

**Payload:**
```yaml
sku: SKU1234
price: -1
```


**Message:** -1 is less than the minimum of 0


---


##### `duplicate tags`

**Status:** ⚠️ WARNING

**Payload:**
```yaml
sku: SKU1234
price: 10
tags:
- key: env
  value: prod
- key: env
  value: prod
```


**Message:** [{'key': 'env', 'value': 'prod'}, {'key': 'env', 'value': 'prod'}] has non-unique elements


---








### sample_schemas.yaml#/components/schemas/Contact <a id="sample-schemas-yaml--components-schemas-contact"></a>





#### Schema Summary

| Metric | Count |
|--------|-------|
| Valid Cases | 5 |
| Invalid Cases | 1 |
| Total Cases | 6 |


#### Valid Test Cases


##### `.components.schemas.Contact.examples[0]`

**Status:** ✅ SUCCESS

**Payload:**
```yaml
email: someone@example.com
```



---


##### `.components.schemas.Contact.examples[1]`

**Status:** ✅ SUCCESS

**Payload:**
```yaml
phone: +49 621 1234567
```



---


##### `.components.schemas.Contact.examples[2]`

**Status:** ❌ ERROR

**Payload:**
```yaml
email: someone@example.com
phone: +49 621 1234567
```


**Message:** {'email': 'someone@example.com', 'phone': '+49 621 1234567'} is not valid under any of the given schemas


---


##### `email contact`

**Status:** ⚠️ WARNING

**Payload:**
```yaml
email: someone@example.com
```



---


##### `parse json string`

**Status:** ✅ SUCCESS

**Payload:**
```yaml
'{"phone":"+4369912345678"}'
```



---





#### Invalid Test Cases


##### `mixed variants`

**Status:** ✅ SUCCESS

**Payload:**
```yaml
email: someone@example.com
phone: +49 621 1234567
```


**Message:** {'email': 'someone@example.com', 'phone': '+49 621 1234567'} is not valid under any of the given schemas


---








### sample_schemas.yaml#/components/schemas/OrderLine <a id="sample-schemas-yaml--components-schemas-orderline"></a>





#### Schema Summary

| Metric | Count |
|--------|-------|
| Valid Cases | 6 |
| Invalid Cases | 3 |
| Total Cases | 9 |


#### Valid Test Cases


##### `.components.schemas.OrderLine.examples[0]`

**Status:** ✅ SUCCESS

**Payload:**
```yaml
sku: SKU1234
unitPrice: 19.99
quantity: 2
```



---


##### `.components.schemas.OrderLine.examples[1]`

**Status:** ✅ SUCCESS

**Payload:**
```yaml
bundleId: B-42
items:
- sku: SKU9
  quantity: 1
```



---


##### `.components.schemas.OrderLine.examples[2]`

**Status:** ❌ ERROR

**Payload:**
```yaml
sku: SKU1
unitPrice: 10
quantity: 1
items:
- sku: SKU2
  quantity: 1
```


**Message:** {'sku': 'SKU1', 'unitPrice': 10, 'quantity': 1, 'items': [{'sku': 'SKU2', 'quantity': 1}]} is not valid under any of the given schemas


---


##### `priced ok`

**Status:** ✅ SUCCESS

**Payload:**
```yaml
sku: SKU1234
unitPrice: 19.99
quantity: 2
```



---


##### `bundled ok`

**Status:** ✅ SUCCESS

**Payload:**
```yaml
bundleId: B-42
items:
- sku: SKU9
  quantity: 1
```



---


##### `priced via json string`

**Status:** ✅ SUCCESS

**Payload:**
```yaml
'{"sku":"SKU7777","unitPrice":0,"quantity":1}'
```



---





#### Invalid Test Cases


##### `mixed properties`

**Status:** ✅ SUCCESS

**Payload:**
```yaml
sku: SKU1
unitPrice: 10
quantity: 1
items:
- sku: SKU2
  quantity: 1
```


**Message:** {'sku': 'SKU1', 'unitPrice': 10, 'quantity': 1, 'items': [{'sku': 'SKU2', 'quantity': 1}]} is not valid under any of the given schemas


---


##### `missing required priced`

**Status:** ✅ SUCCESS

**Payload:**
```yaml
sku: SKU9999
```


**Message:** {'sku': 'SKU9999'} is not valid under any of the given schemas


---


##### `wrong types`

**Status:** ✅ SUCCESS

**Payload:**
```yaml
sku: SKU1234
unitPrice: 10
quantity: 0
```


**Message:** {'sku': 'SKU1234', 'unitPrice': 10, 'quantity': 0} is not valid under any of the given schemas


---








### sample_schemas.yaml#/components/schemas/URI <a id="sample-schemas-yaml--components-schemas-uri"></a>





#### Schema Summary

| Metric | Count |
|--------|-------|
| Valid Cases | 2 |
| Invalid Cases | 1 |
| Total Cases | 3 |


#### Valid Test Cases


##### `.components.schemas.URI.examples[0]`

**Status:** ✅ SUCCESS

**Payload:**
```yaml
https://example.com
```



---


##### `good uri`

**Status:** ✅ SUCCESS

**Payload:**
```yaml
https://example.com
```



---





#### Invalid Test Cases


##### `not a uri`

**Status:** ❌ ERROR

**Payload:**
```yaml
not a uri
```


**Message:** UNEXPECTEDLY VALID
A validator that *ignores* 'format' accepted this instance, while a strict validator (enforcing 'format') might reject it as desired (format: uri).
Consider enforcing the expected format by adding an explicit 'pattern' property to the schema.


---








### sample_schemas.yaml#/components/schemas/DateISO <a id="sample-schemas-yaml--components-schemas-dateiso"></a>





#### Schema Summary

| Metric | Count |
|--------|-------|
| Valid Cases | 2 |
| Invalid Cases | 1 |
| Total Cases | 3 |


#### Valid Test Cases


##### `.components.schemas.DateISO.examples[0]`

**Status:** ✅ SUCCESS

**Payload:**
```yaml
'2025-08-31'
```



---


##### `good date`

**Status:** ✅ SUCCESS

**Payload:**
```yaml
'2025-08-31'
```



---





#### Invalid Test Cases


##### `not a date`

**Status:** ❌ ERROR

**Payload:**
```yaml
31-12-2025
```


**Message:** UNEXPECTEDLY VALID
A validator that *ignores* 'format' accepted this instance, while a strict validator (enforcing 'format') might reject it as desired (format: date).
Consider enforcing the expected format by adding an explicit 'pattern' property to the schema.


---









## Appendix

### Tool Information

| Property | Value |
|----------|-------|
| TeDS Version | 0.1.dev13+g9e84ef6db.d20250920 |
| Supported Spec Range | 1.0-1.0 |
| Recommended Spec Version | 1.0 |
| Report Generation Time | 2025-09-22T15:26:35.676231+02:00 |

### Report Scope

This default report includes:

- **Executive Summary** - High-level overview of validation results
- **Schema Coverage Analysis** - Warnings for incomplete test coverage
- **Detailed Results** - Complete breakdown of all test cases by schema
- **Status Indicators** - Visual distinction between SUCCESS, WARNING, and ERROR states
- **Structured Format** - Organized presentation for easy analysis

For questions about this report or TeDS functionality, please refer to the TeDS documentation.

---

*This report was generated automatically by TeDS (Test-Driven Schema Development Tool).*
