"""PAIR1: `span_logits_loss` equals the model's own shifted cross-entropy on the span-masked labels — on a tiny random
causal LM, CPU, no download."""
import pytest

torch = pytest.importorskip("torch")
transformers = pytest.importorskip("transformers")


def test_span_logits_loss_equals_the_models_own_loss():
    from transformers import LlamaConfig, LlamaForCausalLM
    from training.s4_train import span_logits_loss
    torch.manual_seed(0)
    model = LlamaForCausalLM(LlamaConfig(vocab_size=97, hidden_size=32, intermediate_size=64, num_hidden_layers=2,
                                         num_attention_heads=4, num_key_value_heads=4, max_position_embeddings=64)).eval()
    ids = torch.randint(0, 97, (1, 40))
    labels = torch.full_like(ids, -100)
    labels[0, 12:17] = ids[0, 12:17]                    # two spans the model "wrote"
    labels[0, 30:35] = ids[0, 30:35]
    with torch.no_grad():
        full = model(input_ids=ids, labels=labels).loss
        mine = span_logits_loss(model, {"input_ids": ids, "attention_mask": torch.ones_like(ids), "labels": labels})
        n = (labels[:, 1:] != -100).sum()
        accum = span_logits_loss(model, {"input_ids": ids, "labels": labels}, num_items_in_batch=n)
    assert torch.allclose(full, mine, atol=1e-5) and torch.allclose(full, accum, atol=1e-5)
