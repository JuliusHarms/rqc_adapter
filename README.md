# Review Quality Collector (RQC) Plugin for Janeway

**Created:** 2025, Julius Harms, Freie Universität Berlin

Version: 22.09.2025. This plugin is in development and is not an official plugin by the RQC initiative.

## 1. What It Is

[Review Quality Collector (RQC)](https://reviewqualitycollector.org) is an initiative for improving the quality of scientific peer review. Its core is a mechanism that supplies a reviewer with a receipt for their work for each journal year. The receipt is based on grading each review according to a journal-specific review quality definition.

This repository is a Janeway plugin that realizes a Janeway adapter for the RQC API, by which Janeway reports the reviewing data of individual article submissions to RQC so that RQC can arrange the grading and add the reviews to the respective reviewers' receipts.

**API Documentation:** https://reviewqualitycollector.org/t/api

## 2. How It Works

- Once you register at RQC you will be provided with a `Journal ID` and `API Key` for your journal
- You can then enter these values on the plugin management page in Janeway
- The plugin will add a button **"RQC-grade the reviews"** by which editors can submit the reviewing data for a given submission to RQC in order to trigger the grading (this step is optional for editors)
- The editor may then be redirected to RQC to perform (or not) a grading right away
- The plugin will also intercept the acceptance-decision-making event and send the decision and reviewing data for that submission to RQC
- Should the RQC service be unavailable when data is submitted automatically at decision time, the request will be stored and will be repeated once a day for several days until it goes through

- Reviewers will be asked on their first review of the year for each journal if they want to participate in RQC.
- If they opt not to participate in RQC their identity will be anonymized and their review content will NOT be sent to RQC.

## 3. How to Use It

### 3.1 Installation

1. Clone this repository into the Janeway plugins folder
2. From the src directory run:
   ```bash
   python3 manage.py install_plugins rqc_adapter
   ```
3. Run the Janeway command for required migrations:
   ```bash
   python3 manage.py makemigrations
   ```
   ```bash
   python3 manage.py migrate
   ```
4. Install the cronjob:
   ```bash
   python3 manage.py rqc_install_cronjob --action install
   ```
   - Make sure you have cron and crontab installed
   - You can customize the time at which the cronjob will run by adding the `--time` argument with a number between 0-23 (default is 8 for 8am)
   - Example: `python3 manage.py rqc_install_cronjob --action install --time 10`
   - You need to make sure python is available to cron.
5. Restart your server (Apache, Passenger, etc)

### 3.2 Journal Setup

It is strongly recommended that you disable one-click-access when using the RQC
Plugin. Review data from reviewers that are not logged in can not be sent to RQC due
privacy reasons. If you have one-click-access enabled many reviews will not be sent to RQC defeating
the purpose of using the plugin!

### 3.3 Daily use
1. Navigate to the Plugin Management page in the navigation pane
2. Select **RQC Adapter**
3. Fill out the form with the `Journal ID` and `API Key` provided by RQC

You will then be told if the given credentials could be validated by the RQC service.

## 4. How Janeway Concepts Are Mapped to RQC Concepts

### 4.1 Editor Types

RQC distinguishes between level 1, 2 and 3 editors. This is mapped to Janeway's editor types in the following way:

  **Level 1 editors:** Section editors that are assigned to the submission
  **Level 2:** Currently no roles in Janeway get labeled as level 2 editors.
  **Level 3:** Editors that are assigned to the submission or that are involved in grading the submission 
   via DraftDecisions

Which editors are contacted for grading by RQC and when can be set on the RQC website.

**See also:** https://reviewqualitycollector.org/t/glossary#grading-importance-cannot-can-please-pleease

### 4.2 Editorial Decisions

Janeway's "Conditional Accept" is transmitted to RQC as a minor revision request. This is because RQC only distinguishes between major and minor revisions.

## 5. Limitations

Attachments uploaded by reviewers are not yet transmitted to RQC.

Currently Janeway does not fire the `ON_REVISIONS_REQUESTED` event which means the plugin cannot send a call to RQC when revisions are requested.

## 6. Current Implementation Status

The plugin is currently still in development.

**RQC's implementation status:** https://reviewqualitycollector.org/t/past-and-future#status