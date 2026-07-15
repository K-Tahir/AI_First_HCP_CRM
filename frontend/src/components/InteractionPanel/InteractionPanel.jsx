import React from "react";
import { useSelector } from "react-redux";
import FormField from "./FormField";
import BrowseBar from "../BrowsePanel/BrowseBar";
import "./InteractionPanel.css";

function formatDate(isoDate) {
  if (!isoDate) return null;
  const [y, m, d] = isoDate.split("-");
  if (!y || !m || !d) return isoDate;
  return `${d}/${m}/${y}`;
}

function SentimentBadge({ sentiment, highlighted }) {
  const cls =
    sentiment === "Positive"
      ? "sentiment-badge sentiment-badge--positive"
      : sentiment === "Negative"
      ? "sentiment-badge sentiment-badge--negative"
      : sentiment === "Neutral"
      ? "sentiment-badge sentiment-badge--neutral"
      : "sentiment-badge sentiment-badge--empty";

  return (
    <div className={`field__value field__value--plain${highlighted ? " field-highlight" : ""}`}>
      <span className={cls}>{sentiment || "Not yet assessed"}</span>
    </div>
  );
}

function BooleanPill({ value, trueLabel, falseLabel, highlighted }) {
  return (
    <div className={`field__value field__value--plain${highlighted ? " field-highlight" : ""}`}>
      <span className={`bool-pill${value ? " bool-pill--on" : ""}`}>
        <span className="bool-pill__dot" />
        {value ? trueLabel : falseLabel}
      </span>
    </div>
  );
}

export default function InteractionPanel() {
  const liveInteraction = useSelector((s) => s.interaction.current);
  const highlighted = useSelector((s) => s.interaction.recentlyUpdatedFields);
  const browseActive = useSelector((s) => s.browse.active);
  const browseViewMode = useSelector((s) => s.browse.viewMode);
  const browseRecord = useSelector((s) => s.browse.currentRecord);
  const browseLoading = useSelector((s) => s.browse.loading);

  // Browse mode shows a passively-viewed historical record instead of the
  // AI's current live focus - it's still 100% read-only either way (no
  // onChange handlers exist anywhere in this component in either mode).
  // Field highlighting only ever applies to Live mode, since a browsed
  // record wasn't just changed by the AI this turn.
  const interaction = browseActive ? browseRecord : liveInteraction;
  const is = browseActive ? () => false : (field) => highlighted.includes(field);
  const hasAnyData = interaction && (interaction.hcp_name || interaction.id);
  // "List / Delete" mode renders its own table (inside BrowseBar) in place
  // of the single-record view below - so none of the single-record
  // states (loading/empty/grid) should render underneath it.
  const showSingleRecordView = !(browseActive && browseViewMode === "list");

  return (
    <section className="interaction-panel">
      <div className="interaction-panel__header">
        <h2>Interaction Details</h2>
        <span className="interaction-panel__lock" title="This form is controlled entirely by the AI Assistant">
          🔒 AI-controlled
        </span>
      </div>

      <BrowseBar />

      {showSingleRecordView && browseActive && browseLoading && (
        <div className="interaction-panel__empty">
          <p>Loading record…</p>
        </div>
      )}

      {showSingleRecordView && browseActive && !browseLoading && !hasAnyData && (
        <div className="interaction-panel__empty">
          <div className="interaction-panel__empty-icon">🔍</div>
          <p>No interactions match those filters. Try adjusting or resetting them above.</p>
        </div>
      )}

      {showSingleRecordView && !browseActive && !hasAnyData && (
        <div className="interaction-panel__empty">
          <div className="interaction-panel__empty-icon">💬</div>
          <p>
            No interaction logged yet. Describe a visit to the AI Assistant on the right — this
            panel will populate automatically.
          </p>
        </div>
      )}

      {showSingleRecordView && hasAnyData && (

      <div className="interaction-panel__grid">
        <FormField label="HCP Name" value={interaction.hcp_name} placeholder="Not yet captured" highlighted={is("hcp_name")} />
        <FormField label="Hospital / Clinic" value={interaction.hospital} placeholder="Not yet captured" highlighted={is("hospital")} />
        <FormField label="Specialty" value={interaction.specialty} placeholder="Not yet captured" highlighted={is("specialty")} />
        <FormField label="Interaction Type" value={interaction.interaction_type} placeholder="Not yet captured" highlighted={is("interaction_type")} />
        <FormField label="Interaction Date" value={formatDate(interaction.interaction_date)} placeholder="Not yet captured" highlighted={is("interaction_date")} />
        <FormField label="Follow-up Date" value={formatDate(interaction.follow_up_date)} placeholder="None scheduled" highlighted={is("follow_up_date")} />

        <FormField label="Products Discussed" span highlighted={is("products_discussed")}>
          {interaction.products_discussed && interaction.products_discussed.length > 0 ? (
            <div className="chip-row">
              {interaction.products_discussed.map((p) => (
                <span className="chip" key={p}>
                  {p}
                </span>
              ))}
            </div>
          ) : (
            <span className="field__value--empty-text">Not yet captured</span>
          )}
        </FormField>

        <FormField label="Observed Sentiment" span>
          <SentimentBadge sentiment={interaction.sentiment} highlighted={is("sentiment")} />
        </FormField>

        <FormField label="Brochures Shared" span>
          <BooleanPill
            value={interaction.brochures_shared}
            trueLabel="Shared"
            falseLabel="Not shared"
            highlighted={is("brochures_shared")}
          />
        </FormField>

        <FormField label="Samples Requested" span>
          <BooleanPill
            value={interaction.samples_requested}
            trueLabel="Requested"
            falseLabel="Not requested"
            highlighted={is("samples_requested")}
          />
        </FormField>

        <FormField
          label="Questions Raised"
          value={interaction.questions_raised}
          placeholder="None recorded"
          span
          highlighted={is("questions_raised")}
        />

        <FormField
          label="Discussion Summary"
          value={interaction.discussion_summary}
          placeholder="No summary yet"
          span
          highlighted={is("discussion_summary")}
        />

        <FormField
          label="Notes"
          value={interaction.notes}
          placeholder="No additional notes"
          span
          highlighted={is("notes")}
        />
      </div>
      )}
    </section>
  );
}
