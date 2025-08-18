# Review Quality Collector (RQC) plugin for Janeway

created 2025, Julius Harms

Version 15.08.2025
Status: **beta test, please ask if you want to participate**

## 1. What it is

[Review Quality Collector (RQC)](https://reviewqualitycollector.org)
is an initiative for improving the quality of
scientific peer review.
Its core is a mechanism that supplies a reviewer with a receipt for
their work for each journal year.
The receipt is based on grading each review according to a journal-specific
review quality definition.

This repository is a Janeway plugin that realizes
a Janeway adapter for the RQC API, by which Janeway
reports the reviewing data of individual article
submissions to RQC so that RQC can arrange the grading and add the
reviews to the respective reviewers' receipts.

Find the RQC API description at
https://reviewqualitycollector.org/t/api.

## 2. How it works

- Provides journal-specific settings
  `rqcJournalId` and `rqcJournalAPIKey`
  that identify the journal's representation on RQC.
- When both are filled, they are checked against RQC
  whether they are a valid pair and rejected if not.
- If they are accepted, they are stored as additional JournalSettings.
- If these settings exist, the plugin will add a button "RQC-grade the reviews"
  by which editors can submit the reviewing data for a given
  submission to RQC in order to trigger the grading.
  This step is optional for the editors.
  Depending on how RQC is configured for that journal, the given
  editor may then be redirected to RQC to perform (or not)
  a grading right away.
- The plugin will also intercept the acceptance-decision-making
  event and send the decision and reviewing data for that submission
  to RQC then.
- Should the RQC service be unavailable when data is submitted
  automatically at decision time, the request will be stored
  and will be repeated once a day for several days until it goes through.

## 3. How to use it

### 3.1 Installation

### 3.2 Journal setup

### 3.3 Daily use

## 4. How OJS concepts are mapped to RQC concepts

## 5. Limitations