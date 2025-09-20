# Why This Matters — Deep Dives

This page collects concrete, real‑world scenarios and shows how TeDS helps avoid or catch those issues early. Each section links back to a concise summary in the README.

## Formats (email, URI, date‑time)

- Real world:
  - OpenAPITools/openapi-generator: date-time leads to wrong client typing/handling in popular generators: https://github.com/OpenAPITools/openapi-generator/issues/9380
  - thephpleague/openapi-psr7-validator: date-time validation allowed non‑RFC3339 strings: https://github.com/thephpleague/openapi-psr7-validator/issues/247
- How TeDS helps:
  - Add negative `date-time` cases (e.g., missing offset) and verify — WARNING/ERROR reveals divergence; enforce determinism via a `pattern`.

## Boundary Conditions (min/max, lengths, items)

- Real world:
  - Schemathesis/OpenAPI: empty array with `minItems: 0` treated as invalid (edge interpretation): https://github.com/schemathesis/schemathesis/issues/3056
  - Kubernetes API linter discussions around `MinItems` and array field pointers: https://github.com/kubernetes-sigs/kube-api-linter/issues/116
- How TeDS helps:
  - Add cases at N−1, N, N+1 (e.g., empty vs. non‑empty arrays) so regressions surface and intent is explicit.

## Enum Drift (casing, widening, narrowing)

- Real world:
  - open-api (express middleware) discussion: case-insensitive enums expected by clients: https://github.com/kogosoftwarellc/open-api/issues/755
  - swift-openapi-generator: request for case-insensitive enums: https://github.com/apple/swift-openapi-generator/issues/721
- How TeDS helps:
  - Add a lowercase/variant invalid case. If it passes, you’ve exposed an acceptance gap; if it fails, you’ve documented strict casing for clients.

## Additional Properties (unknown fields)

- Real world:
  - JSON schema: allOf with additionalProperties: https://stackoverflow.com/questions/22689900/json-schema-allof-with-additionalproperties
  - Understanding additionalProperties: https://stackoverflow.com/questions/16459954/understanding-the-additionalproperties-keyword-in-json-schema-draft-version-4
- How TeDS helps:
  - Add an invalid case with an unknown field. If it’s accepted, the schema is too lax; if rejected, the test documents strictness and prevents accidental relaxations.

## Pointers & Compositions (oneOf/anyOf)

- Real world:
  - Numerous issues and Q&As around `oneOf`/`anyOf` usage and expectations, e.g.: https://stackoverflow.com/questions/25014650/json-schema-example-for-oneof-objects
- How TeDS helps:
  - Craft a no‑match and ambiguous‑match invalid case to lock in intent; you’ll catch ambiguity and refine `oneOf`/`anyOf`.
