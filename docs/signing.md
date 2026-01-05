# Signing

This SDK matches the current RootLayer/IntentManager signature verification.

## Important: this is EIP-191 (ethers `signMessage`), not standard EIP-712

The on-chain and RootLayer verification uses:

1. `digest = keccak256(abi.encode(...))`
2. `signature = signMessage(bytes(digest))` (EIP-191 prefix: `"\x19Ethereum Signed Message:\n32"`)

So the SDK exposes digest builders + `Signer.sign_message_32(digest32)`.

## Typehashes

- Intent: `PIN_INTENT_V1(bytes32,bytes32,address,bytes32,bytes32,uint256,address,uint256,address,uint256)`
- Assignment: `PIN_ASSIGNMENT_V1(bytes32,bytes32,bytes32,address,uint8,address,address,uint256)`
- Validation: `PIN_VALIDATION_V1(bytes32,bytes32,bytes32,address,bytes32,bytes32,uint64,bytes32,address,uint256)`
- ValidationBatch: `PIN_VALIDATION_BATCH_V1(bytes32,bytes32,uint64,bytes32,address,uint256)`
- DirectIntent: `PIN_DIRECT_INTENT_V1(bytes32,bytes32,address,bytes32,bytes32,uint256,address,uint256,address,address,uint256)`

All digests include `(intentManagerAddress, chainId)` at the end for replay protection.

## Params hash

`params_hash = keccak256(intent_raw || metadata)` (byte concatenation).

## Validation batch items hash

`items_hash = keccak256(abi.encode(items))` where `items` is an array of tuples:

`(intent_id, assignment_id, agent, result_hash, proof_hash)`

`executed_at` is **NOT** part of `items_hash`.
