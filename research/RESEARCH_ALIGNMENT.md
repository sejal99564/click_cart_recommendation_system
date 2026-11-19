# Research alignment and reproducibility

**Primary source:** Prajapati, Kumar, Prasad, Rai, Kumar, and Kumar, *Artificial Intelligence in Retail and E-commerce: Transforming Customer Experience*, supplied six-page PDF. Page references below follow PDF pagination.

## Framework and implementation scope

The paper integrates personalized recommendation, conversational support, and adaptive pricing to improve customer discovery, engagement, and retail decisions. Its architecture connects acquisition devices, controlled cloud/database storage, Python AI services, and web/mobile applications. New interactions can feed later training. Privacy, security, trust, fairness, transparency, and customer control are design objectives (Sections I, III, V–VII).

| Component | Paper method | Shopwise AI mapping and evidence gap |
|---|---|---|
| Data pipeline | Section IV-A collects customer, product, transaction, browsing, inquiry, and interaction data. It deduplicates, handles missing and invalid records, encodes categories and text, normalizes where necessary, joins features, and splits train/test data. | Shopwise AI persists catalog and collection data and uses opt-in search history. Experiments use generated datasets. The paper gives no named dataset, dataset sizes, label definition, split protocol, or fitted preprocessing configuration. |
| Recommendations | Sections III-C and IV-B describe content-based and collaborative approaches and recommend a hybrid when both product attributes and behavioral data exist. | Shopwise AI compares content and collaborative signals in a synthetic experiment and ranks the demo catalog using account preferences and behavior. The paper does not specify feature weights, similarity formulas, training parameters, or ranking evaluation. |
| Conversational support | Sections III-C and IV-B describe answering customer questions and identify communication quality, trust, convenience, and risk as concerns. | The Shopwise AI assistant queries catalog records using a structured tool and stores account-owned history. The PDF gives no concrete model, prompt, test set, or task-specific evaluation. |
| Dynamic pricing | Sections III-C and IV-B cite deep reinforcement learning from Yin and Han as an approach for adaptive pricing with behavioral and market signals. | Shopwise AI uses supervised pricing baselines for a simulated merchant. The PDF omits states, actions, reward, simulator, and per-service pricing results. |
| Integration | Sections IV-C and V outline preprocessing, task-specific inference, test evaluation, delivery, and interaction logging. | Next.js and FastAPI integrate the storefront, SQL-backed catalog and account state, recommendation ranking, and catalog-grounded chat. The pricing lab uses parameters from the synthetic model artifact. |

## Original paper results

Section VI-A, Table I (PDF p. 5) reports the following percentages.

| Model | Accuracy | Precision | Recall | F1 |
|---|---:|---:|---:|---:|
| Logistic regression | 89.4 | 88.7 | 87.9 | 88.3 |
| Random forest | 93.1 | 92.6 | 92.2 | 92.4 |
| XGBoost | 95.0 | 94.5 | 94.1 | 94.3 |
| Proposed hybrid AI model | 96.7 | 96.2 | 95.9 | 96.0 |

## Reproduced and new results

No exact reproduction has been run. It requires the original dataset, target and split definitions, model configurations and hybrid architecture, and metric averaging rules. The paper does not supply service-specific ranking, conversational, or pricing metrics.

Shopwise AI ran separate synthetic experiments with seed 42. Recommendations compare popularity, category-based similarity, item co-occurrence cosine, and a fixed-weight hybrid. Evaluation holds back the final three synthetic interactions per user and measures ranking and catalog metrics at K=5. Pricing evaluates ridge and random forest predictions against historical simulated merchant prices on the final 80 of 400 time steps. The target is a profit-maximizing price under the documented demand simulator. This supervised pricing experiment differs from the reinforcement-learning approach the source paper discusses.

The downloadable report records library versions, dataset sizes, splits, and measured results. Run `python -m ml.run_experiments` from the project root to regenerate it and save the model artifacts. The synthetic results do not establish performance on real shopping behavior.
