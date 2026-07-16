/* zoomfetch -- a tiny Z39.50 fetch driver over YAZ's ZOOM API (issue #85).
 *
 * Replaces the old approach of scripting the interactive yaz-client and
 * reconstructing which record answers which query *by position* (the source of
 * the "unalignable" bug). ZOOM gives us a result-set object per search and
 * discrete record objects, so every record is unambiguously tied to its query
 * by an explicit id -- no positional inference.
 *
 * Usage:
 *   zoomfetch [--syntax usmarc] [--sleep 0.4] [--maxrecords 3] [--timeout 45] TARGET
 *
 *   TARGET is a ZOOM connection string, e.g. tcp:afton.lib.unc.edu:210/INNOPAC.
 *   One persistent ZOOM_connection is opened and reused for every job, so the
 *   Init handshake is amortised across the whole batch (as the old batching did)
 *   but with no alignment risk.
 *
 * stdin: one job per line, tab-separated:
 *     <id> \t <pqf-query> [\t <maxrecords>]
 *   <id> is an opaque token echoed back verbatim on every line for that job.
 *   <pqf-query> is a PQF (prefix) query, exactly what marc_harvest.py emits
 *   (e.g. `@attr 1=7 9780262232586`). <maxrecords> overrides --maxrecords for
 *   this job (mirrors the old per-server show_n).
 *
 * stdout (binary-safe, since MARC records are binary): a stream of framed lines.
 * For each job, in input order:
 *     HITS   \t <id> \t <hitcount>\n                  (search succeeded)
 *     RECORD \t <id> \t <index> \t <bytelen>\n        followed by exactly
 *                                                     <bytelen> raw ISO 2709
 *                                                     bytes then a '\n'
 *     ERROR  \t <id> \t <code> \t <message>\n         (server search diagnostic;
 *                                                     a real miss, not retryable)
 *     FATAL  \t <id> \t <code> \t <message>\n         (connection-level failure:
 *                                                     the connection is gone, so
 *                                                     processing stops here and
 *                                                     the remaining jobs get no
 *                                                     line -- the caller defers
 *                                                     every unanswered job)
 * A job that produced a HITS or ERROR line was actually tested (record it); a job
 * with no line at all (FATAL cut the session short, or the driver never reached
 * it) was not, so the caller leaves it unattempted to retry next run.
 *
 * The server's raw record bytes are emitted untouched: the existing UTF-8 / UNC
 * leader-09 handling stays downstream (`yaz-marcdump -l 9=97` in marc_harvest.py).
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <yaz/zoom.h>

/* Framed output for one retrieved record: a length-prefixed header line, then
 * the raw bytes, then a newline. All record I/O is on stdout in binary. */
static void emit_record(const char *id, int index, const char *buf, int len)
{
    printf("RECORD\t%s\t%d\t%d\n", id, index, len);
    if (len > 0)
        fwrite(buf, 1, (size_t)len, stdout);
    putchar('\n');
}

/* Run one job over the shared connection. Returns 1 to keep going, 0 if the
 * connection is dead (a FATAL was emitted) and the caller should stop. */
static int run_job(ZOOM_connection conn, const char *id, const char *pqf,
                   int maxrecords)
{
    const char *errmsg = NULL, *addinfo = NULL;
    ZOOM_query q = ZOOM_query_create();
    if (ZOOM_query_prefix(q, pqf) != 0) {
        /* Malformed PQF -- a client-side query error, not a server drop. Report
         * it as a (non-retryable) miss and keep the connection for later jobs. */
        printf("ERROR\t%s\t%d\t%s\n", id, ZOOM_ERROR_INVALID_QUERY, "invalid pqf");
        ZOOM_query_destroy(q);
        return 1;
    }

    ZOOM_resultset rs = ZOOM_connection_search(conn, q);
    ZOOM_query_destroy(q);

    int code = ZOOM_connection_error(conn, &errmsg, &addinfo);
    if (code != 0) {
        /* Codes >= 10000 are ZOOM/connection-level failures (connect lost, init,
         * timeout, decode): the connection can't be trusted for the rest of the
         * batch, so stop. Codes < 10000 are Bib-1 search diagnostics (e.g. an
         * unsupported attribute) -- a genuine per-query failure; report and move
         * on. */
        if (code >= 10000) {
            printf("FATAL\t%s\t%d\t%s\n", id, code, errmsg ? errmsg : "");
            if (rs) ZOOM_resultset_destroy(rs);
            return 0;
        }
        printf("ERROR\t%s\t%d\t%s\n", id, code, errmsg ? errmsg : "");
        if (rs) ZOOM_resultset_destroy(rs);
        return 1;
    }

    size_t n = ZOOM_resultset_size(rs);
    printf("HITS\t%s\t%zu\n", id, n);

    size_t want = (size_t)maxrecords;
    if (want > n)
        want = n;
    for (size_t k = 0; k < want; k++) {
        ZOOM_record rec = ZOOM_resultset_record(rs, k);
        code = ZOOM_connection_error(conn, &errmsg, &addinfo);
        if (code != 0) {
            /* The connection dropped mid-Present. Whatever we already printed for
             * this job stands; stop the batch so the caller defers the rest. */
            printf("FATAL\t%s\t%d\t%s\n", id, code, errmsg ? errmsg : "");
            ZOOM_resultset_destroy(rs);
            return 0;
        }
        if (!rec)
            continue;
        int len = 0;
        const char *raw = ZOOM_record_get(rec, "raw", &len);
        if (raw && len > 0)
            emit_record(id, (int)k, raw, len);
    }
    ZOOM_resultset_destroy(rs);
    return 1;
}

int main(int argc, char **argv)
{
    const char *syntax = "usmarc";
    const char *target = NULL;
    double sleep_s = 0.0;
    int maxrecords = 1;
    const char *timeout = "45";

    for (int i = 1; i < argc; i++) {
        if (!strcmp(argv[i], "--syntax") && i + 1 < argc)
            syntax = argv[++i];
        else if (!strcmp(argv[i], "--sleep") && i + 1 < argc)
            sleep_s = atof(argv[++i]);
        else if (!strcmp(argv[i], "--maxrecords") && i + 1 < argc)
            maxrecords = atoi(argv[++i]);
        else if (!strcmp(argv[i], "--timeout") && i + 1 < argc)
            timeout = argv[++i];
        else if (argv[i][0] == '-') {
            fprintf(stderr, "zoomfetch: unknown option %s\n", argv[i]);
            return 2;
        } else
            target = argv[i];
    }
    if (!target) {
        fprintf(stderr, "usage: zoomfetch [--syntax S] [--sleep SEC] "
                        "[--maxrecords N] [--timeout SEC] TARGET\n");
        return 2;
    }

    ZOOM_connection conn = ZOOM_connection_new(target, 0);
    ZOOM_connection_option_set(conn, "preferredRecordSyntax", syntax);
    ZOOM_connection_option_set(conn, "timeout", timeout);

    char *line = NULL;
    size_t cap = 0;
    ssize_t nread;
    int alive = 1;
    while ((nread = getline(&line, &cap, stdin)) != -1) {
        if (nread > 0 && line[nread - 1] == '\n')
            line[--nread] = '\0';
        if (nread == 0)
            continue;

        /* id \t query [\t maxrecords] -- split on the first two tabs only, since
         * a PQF query itself contains spaces (never tabs). */
        char *t1 = strchr(line, '\t');
        if (!t1)
            continue;                 /* malformed line: no query */
        *t1 = '\0';
        char *id = line;
        char *query = t1 + 1;
        int job_max = maxrecords;
        char *t2 = strchr(query, '\t');
        if (t2) {
            *t2 = '\0';
            int m = atoi(t2 + 1);
            if (m > 0)
                job_max = m;
        }

        if (alive)
            alive = run_job(conn, id, query, job_max);
        /* Once the connection is dead, stop querying but keep draining stdin so
         * the writer doesn't get SIGPIPE; the unanswered jobs simply get no line
         * and the caller defers them. */
        fflush(stdout);
        if (alive && sleep_s > 0.0)
            usleep((useconds_t)(sleep_s * 1e6));
    }

    free(line);
    ZOOM_connection_destroy(conn);
    return 0;
}
