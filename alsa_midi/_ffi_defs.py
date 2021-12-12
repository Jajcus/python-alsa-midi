"""
ALSA library API cffi definitions.
"""

from cffi import FFI

ffi = FFI()

C_SOURCE = """
#include <alsa/asoundlib.h>
"""

C_DEFS_PACKED = r"""
struct snd_seq_ev_ext {
    unsigned int len;       /**< length of data */
    void *ptr;          /**< pointer to data (note: can be 64-bit) */
};
"""

C_DEFS = r"""
/*************************************************************************************************/

/* global.h */

const char *snd_asoundlib_version(void);

void *snd_dlopen(const char *file, int mode, char *errbuf, size_t errbuflen);
void *snd_dlsym(void *handle, const char *name, const char *version);
int snd_dlclose(void *handle);

typedef struct _snd_async_handler snd_async_handler_t;

typedef void (*snd_async_callback_t)(snd_async_handler_t *handler);

int snd_async_add_handler(snd_async_handler_t **handler, int fd,
              snd_async_callback_t callback, void *private_data);
int snd_async_del_handler(snd_async_handler_t *handler);
int snd_async_handler_get_fd(snd_async_handler_t *handler);
int snd_async_handler_get_signo(snd_async_handler_t *handler);
void *snd_async_handler_get_callback_private(snd_async_handler_t *handler);

struct snd_shm_area *snd_shm_area_create(int shmid, void *ptr);
struct snd_shm_area *snd_shm_area_share(struct snd_shm_area *area);
int snd_shm_area_destroy(struct snd_shm_area *area);

int snd_user_file(const char *file, char **result);

typedef struct timeval snd_timestamp_t;
typedef struct timespec snd_htimestamp_t;

/*************************************************************************************************/

/* error.h */

const char *snd_strerror(int errnum);

/*************************************************************************************************/

/* conf.h */

typedef enum _snd_config_type {
        SND_CONFIG_TYPE_INTEGER,
        SND_CONFIG_TYPE_INTEGER64,
        SND_CONFIG_TYPE_REAL,
        SND_CONFIG_TYPE_STRING,
        SND_CONFIG_TYPE_POINTER,
    SND_CONFIG_TYPE_COMPOUND = 1024
} snd_config_type_t;

typedef struct _snd_config snd_config_t;


/*************************************************************************************************/

/* seq_event.h */

typedef unsigned char snd_seq_event_type_t;

enum snd_seq_event_type {
    SND_SEQ_EVENT_SYSTEM = 0,
    SND_SEQ_EVENT_RESULT,
    SND_SEQ_EVENT_NOTE = 5,
    SND_SEQ_EVENT_NOTEON,
    SND_SEQ_EVENT_NOTEOFF,
    SND_SEQ_EVENT_KEYPRESS,
    SND_SEQ_EVENT_CONTROLLER = 10,
    SND_SEQ_EVENT_PGMCHANGE,
    SND_SEQ_EVENT_CHANPRESS,
    SND_SEQ_EVENT_PITCHBEND,
    SND_SEQ_EVENT_CONTROL14,
    SND_SEQ_EVENT_NONREGPARAM,
    SND_SEQ_EVENT_REGPARAM,
    SND_SEQ_EVENT_SONGPOS = 20,
    SND_SEQ_EVENT_SONGSEL,
    SND_SEQ_EVENT_QFRAME,
    SND_SEQ_EVENT_TIMESIGN,
    SND_SEQ_EVENT_KEYSIGN,

    SND_SEQ_EVENT_START = 30,
    SND_SEQ_EVENT_CONTINUE,
    SND_SEQ_EVENT_STOP,
    SND_SEQ_EVENT_SETPOS_TICK,
    SND_SEQ_EVENT_SETPOS_TIME,
    SND_SEQ_EVENT_TEMPO,
    SND_SEQ_EVENT_CLOCK,
    SND_SEQ_EVENT_TICK,
    SND_SEQ_EVENT_QUEUE_SKEW,
    SND_SEQ_EVENT_SYNC_POS,

    SND_SEQ_EVENT_TUNE_REQUEST = 40,
    SND_SEQ_EVENT_RESET,
    SND_SEQ_EVENT_SENSING,

    SND_SEQ_EVENT_ECHO = 50,
    SND_SEQ_EVENT_OSS,

    SND_SEQ_EVENT_CLIENT_START = 60,
    SND_SEQ_EVENT_CLIENT_EXIT,
    SND_SEQ_EVENT_CLIENT_CHANGE,
    SND_SEQ_EVENT_PORT_START,
    SND_SEQ_EVENT_PORT_EXIT,
    SND_SEQ_EVENT_PORT_CHANGE,

    SND_SEQ_EVENT_PORT_SUBSCRIBED,
    SND_SEQ_EVENT_PORT_UNSUBSCRIBED,

    SND_SEQ_EVENT_USR0 = 90,
    SND_SEQ_EVENT_USR1,
    SND_SEQ_EVENT_USR2,
    SND_SEQ_EVENT_USR3,
    SND_SEQ_EVENT_USR4,
    SND_SEQ_EVENT_USR5,
    SND_SEQ_EVENT_USR6,
    SND_SEQ_EVENT_USR7,
    SND_SEQ_EVENT_USR8,
    SND_SEQ_EVENT_USR9,

    SND_SEQ_EVENT_SYSEX = 130,
    SND_SEQ_EVENT_BOUNCE,
    SND_SEQ_EVENT_USR_VAR0 = 135,
    SND_SEQ_EVENT_USR_VAR1,
    SND_SEQ_EVENT_USR_VAR2,
    SND_SEQ_EVENT_USR_VAR3,
    SND_SEQ_EVENT_USR_VAR4,
    SND_SEQ_EVENT_NONE = 255
};

typedef struct snd_seq_addr {
    unsigned char client;   /**< Client id */
    unsigned char port; /**< Port id */
} snd_seq_addr_t;

typedef struct snd_seq_connect {
    snd_seq_addr_t sender;  /**< sender address */
    snd_seq_addr_t dest;    /**< destination address */
} snd_seq_connect_t;

typedef struct snd_seq_real_time {
    unsigned int tv_sec;        /**< seconds */
    unsigned int tv_nsec;       /**< nanoseconds */
} snd_seq_real_time_t;

typedef unsigned int snd_seq_tick_time_t;

typedef union snd_seq_timestamp {
    snd_seq_tick_time_t tick;   /**< tick-time */
    struct snd_seq_real_time time;  /**< real-time */
} snd_seq_timestamp_t;


#define SND_SEQ_TIME_STAMP_TICK     0
#define SND_SEQ_TIME_STAMP_REAL     1
#define SND_SEQ_TIME_STAMP_MASK     1

#define SND_SEQ_TIME_MODE_ABS       0
#define SND_SEQ_TIME_MODE_REL       2
#define SND_SEQ_TIME_MODE_MASK      2

#define SND_SEQ_EVENT_LENGTH_FIXED  0
#define SND_SEQ_EVENT_LENGTH_VARIABLE   4
#define SND_SEQ_EVENT_LENGTH_VARUSR 8
#define SND_SEQ_EVENT_LENGTH_MASK   12

#define SND_SEQ_PRIORITY_NORMAL     0
#define SND_SEQ_PRIORITY_HIGH       16
#define SND_SEQ_PRIORITY_MASK       16

typedef struct snd_seq_ev_note {
    unsigned char channel;      /**< channel number */
    unsigned char note;     /**< note */
    unsigned char velocity;     /**< velocity */
    unsigned char off_velocity; /**< note-off velocity; only for #SND_SEQ_EVENT_NOTE */
    unsigned int duration;      /**< duration until note-off; only for #SND_SEQ_EVENT_NOTE */
} snd_seq_ev_note_t;

typedef struct snd_seq_ev_ctrl {
    unsigned char channel;      /**< channel number */
    unsigned char unused[3];    /**< reserved */
    unsigned int param;     /**< control parameter */
    signed int value;       /**< control value */
} snd_seq_ev_ctrl_t;

typedef struct snd_seq_ev_raw8 {
    unsigned char d[12];        /**< 8 bit value */
} snd_seq_ev_raw8_t;

typedef struct snd_seq_ev_raw32 {
    unsigned int d[3];      /**< 32 bit value */
} snd_seq_ev_raw32_t;

typedef struct snd_seq_ev_ext snd_seq_ev_ext_t;

typedef struct snd_seq_result {
    int event;      /**< processed event type */
    int result;     /**< status */
} snd_seq_result_t;

typedef struct snd_seq_queue_skew {
    unsigned int value; /**< skew value */
    unsigned int base;  /**< skew base */
} snd_seq_queue_skew_t;

typedef struct snd_seq_ev_queue_control {
    unsigned char queue;            /**< affected queue */
    unsigned char unused[3];        /**< reserved */
    union {
        signed int value;       /**< affected value (e.g. tempo) */
        snd_seq_timestamp_t time;   /**< time */
        unsigned int position;      /**< sync position */
        snd_seq_queue_skew_t skew;  /**< queue skew */
        unsigned int d32[2];        /**< any data */
        unsigned char d8[8];        /**< any data */
    } param;                /**< data value union */
} snd_seq_ev_queue_control_t;

typedef struct snd_seq_event {
    snd_seq_event_type_t type;  /**< event type */
    unsigned char flags;        /**< event flags */
    unsigned char tag;      /**< tag */

    unsigned char queue;        /**< schedule queue */
    snd_seq_timestamp_t time;   /**< schedule time */

    snd_seq_addr_t source;      /**< source address */
    snd_seq_addr_t dest;        /**< destination address */

    union {
        snd_seq_ev_note_t note;     /**< note information */
        snd_seq_ev_ctrl_t control;  /**< MIDI control information */
        snd_seq_ev_raw8_t raw8;     /**< raw8 data */
        snd_seq_ev_raw32_t raw32;   /**< raw32 data */
        snd_seq_ev_ext_t ext;       /**< external data */
        snd_seq_ev_queue_control_t queue; /**< queue control */
        snd_seq_timestamp_t time;   /**< timestamp */
        snd_seq_addr_t addr;        /**< address */
        snd_seq_connect_t connect;  /**< connect information */
        snd_seq_result_t result;    /**< operation result code */
    } data;             /**< event data... */
} snd_seq_event_t;


/*************************************************************************************************/

/* timer.h */

typedef struct _snd_timer_id snd_timer_id_t;
typedef struct _snd_timer_ginfo snd_timer_ginfo_t;
typedef struct _snd_timer_gparams snd_timer_gparams_t;
typedef struct _snd_timer_gstatus snd_timer_gstatus_t;
typedef struct _snd_timer_info snd_timer_info_t;
typedef struct _snd_timer_params snd_timer_params_t;
typedef struct _snd_timer_status snd_timer_status_t;
typedef enum _snd_timer_class {
    SND_TIMER_CLASS_NONE = -1,  /**< invalid */
    SND_TIMER_CLASS_SLAVE = 0,  /**< slave timer */
    SND_TIMER_CLASS_GLOBAL,     /**< global timer */
    SND_TIMER_CLASS_CARD,       /**< card timer */
    SND_TIMER_CLASS_PCM,        /**< PCM timer */
    SND_TIMER_CLASS_LAST = SND_TIMER_CLASS_PCM  /**< last timer */
} snd_timer_class_t;
typedef enum _snd_timer_slave_class {
    SND_TIMER_SCLASS_NONE = 0,      /**< none */
    SND_TIMER_SCLASS_APPLICATION,       /**< for internal use */
    SND_TIMER_SCLASS_SEQUENCER,     /**< sequencer timer */
    SND_TIMER_SCLASS_OSS_SEQUENCER,     /**< OSS sequencer timer */
    SND_TIMER_SCLASS_LAST = SND_TIMER_SCLASS_OSS_SEQUENCER  /**< last slave timer */
} snd_timer_slave_class_t;
typedef enum _snd_timer_event {
    SND_TIMER_EVENT_RESOLUTION = 0, /* val = resolution in ns */
    SND_TIMER_EVENT_TICK,       /* val = ticks */
    SND_TIMER_EVENT_START,      /* val = resolution in ns */
    SND_TIMER_EVENT_STOP,       /* val = 0 */
    SND_TIMER_EVENT_CONTINUE,   /* val = resolution in ns */
    SND_TIMER_EVENT_PAUSE,      /* val = 0 */
    SND_TIMER_EVENT_EARLY,      /* val = 0 */
    SND_TIMER_EVENT_SUSPEND,    /* val = 0 */
    SND_TIMER_EVENT_RESUME,     /* val = resolution in ns */
    /* master timer events for slave timer instances */
    SND_TIMER_EVENT_MSTART = SND_TIMER_EVENT_START + 10,
    SND_TIMER_EVENT_MSTOP = SND_TIMER_EVENT_STOP + 10,
    SND_TIMER_EVENT_MCONTINUE = SND_TIMER_EVENT_CONTINUE + 10,
    SND_TIMER_EVENT_MPAUSE = SND_TIMER_EVENT_PAUSE + 10,
    SND_TIMER_EVENT_MSUSPEND = SND_TIMER_EVENT_SUSPEND + 10,
    SND_TIMER_EVENT_MRESUME = SND_TIMER_EVENT_RESUME + 10
} snd_timer_event_t;
typedef struct _snd_timer_read {
    unsigned int resolution;    /**< tick resolution in nanoseconds */
        unsigned int ticks;     /**< count of happened ticks */
} snd_timer_read_t;

#define SND_TIMER_GLOBAL_SYSTEM 0
#define SND_TIMER_GLOBAL_RTC    1   /* Obsoleted, due to enough legacy. */
#define SND_TIMER_GLOBAL_HPET   2
#define SND_TIMER_GLOBAL_HRTIMER 3

#define SND_TIMER_OPEN_NONBLOCK     0
#define SND_TIMER_OPEN_TREAD        2

typedef enum _snd_timer_type {
    /** Kernel level HwDep */
    SND_TIMER_TYPE_HW = 0,
    /** Shared memory client timer (not yet implemented) */
    SND_TIMER_TYPE_SHM,
    /** INET client timer (not yet implemented) */
    SND_TIMER_TYPE_INET
} snd_timer_type_t;

typedef struct _snd_timer_query snd_timer_query_t;
typedef struct _snd_timer snd_timer_t;

int snd_timer_query_open(snd_timer_query_t **handle, const char *name, int mode);
int snd_timer_query_open_lconf(snd_timer_query_t **handle, const char *name,
                               int mode, snd_config_t *lconf);
int snd_timer_query_close(snd_timer_query_t *handle);
int snd_timer_query_next_device(snd_timer_query_t *handle, snd_timer_id_t *tid);
int snd_timer_query_info(snd_timer_query_t *handle, snd_timer_ginfo_t *info);
int snd_timer_query_params(snd_timer_query_t *handle, snd_timer_gparams_t *params);
int snd_timer_query_status(snd_timer_query_t *handle, snd_timer_gstatus_t *status);

int snd_timer_open(snd_timer_t **handle, const char *name, int mode);
int snd_timer_open_lconf(snd_timer_t **handle, const char *name, int mode, snd_config_t *lconf);
int snd_timer_close(snd_timer_t *handle);
int snd_async_add_timer_handler(snd_async_handler_t **handler, snd_timer_t *timer,
                snd_async_callback_t callback, void *private_data);
snd_timer_t *snd_async_handler_get_timer(snd_async_handler_t *handler);
int snd_timer_poll_descriptors_count(snd_timer_t *handle);
int snd_timer_poll_descriptors(snd_timer_t *handle, struct pollfd *pfds, unsigned int space);
int snd_timer_poll_descriptors_revents(snd_timer_t *timer, struct pollfd *pfds,
                                       unsigned int nfds, unsigned short *revents);
int snd_timer_info(snd_timer_t *handle, snd_timer_info_t *timer);
int snd_timer_params(snd_timer_t *handle, snd_timer_params_t *params);
int snd_timer_status(snd_timer_t *handle, snd_timer_status_t *status);
int snd_timer_start(snd_timer_t *handle);
int snd_timer_stop(snd_timer_t *handle);
int snd_timer_continue(snd_timer_t *handle);
ssize_t snd_timer_read(snd_timer_t *handle, void *buffer, size_t size);

size_t snd_timer_id_sizeof(void);
int snd_timer_id_malloc(snd_timer_id_t **ptr);
void snd_timer_id_free(snd_timer_id_t *obj);
void snd_timer_id_copy(snd_timer_id_t *dst, const snd_timer_id_t *src);

void snd_timer_id_set_class(snd_timer_id_t *id, int dev_class);
int snd_timer_id_get_class(snd_timer_id_t *id);
void snd_timer_id_set_sclass(snd_timer_id_t *id, int dev_sclass);
int snd_timer_id_get_sclass(snd_timer_id_t *id);
void snd_timer_id_set_card(snd_timer_id_t *id, int card);
int snd_timer_id_get_card(snd_timer_id_t *id);
void snd_timer_id_set_device(snd_timer_id_t *id, int device);
int snd_timer_id_get_device(snd_timer_id_t *id);
void snd_timer_id_set_subdevice(snd_timer_id_t *id, int subdevice);
int snd_timer_id_get_subdevice(snd_timer_id_t *id);

size_t snd_timer_ginfo_sizeof(void);
int snd_timer_ginfo_malloc(snd_timer_ginfo_t **ptr);
void snd_timer_ginfo_free(snd_timer_ginfo_t *obj);
void snd_timer_ginfo_copy(snd_timer_ginfo_t *dst, const snd_timer_ginfo_t *src);

int snd_timer_ginfo_set_tid(snd_timer_ginfo_t *obj, snd_timer_id_t *tid);
snd_timer_id_t *snd_timer_ginfo_get_tid(snd_timer_ginfo_t *obj);
unsigned int snd_timer_ginfo_get_flags(snd_timer_ginfo_t *obj);
int snd_timer_ginfo_get_card(snd_timer_ginfo_t *obj);
char *snd_timer_ginfo_get_id(snd_timer_ginfo_t *obj);
char *snd_timer_ginfo_get_name(snd_timer_ginfo_t *obj);
unsigned long snd_timer_ginfo_get_resolution(snd_timer_ginfo_t *obj);
unsigned long snd_timer_ginfo_get_resolution_min(snd_timer_ginfo_t *obj);
unsigned long snd_timer_ginfo_get_resolution_max(snd_timer_ginfo_t *obj);
unsigned int snd_timer_ginfo_get_clients(snd_timer_ginfo_t *obj);

size_t snd_timer_info_sizeof(void);
int snd_timer_info_malloc(snd_timer_info_t **ptr);
void snd_timer_info_free(snd_timer_info_t *obj);
void snd_timer_info_copy(snd_timer_info_t *dst, const snd_timer_info_t *src);

int snd_timer_info_is_slave(snd_timer_info_t * info);
int snd_timer_info_get_card(snd_timer_info_t * info);
const char *snd_timer_info_get_id(snd_timer_info_t * info);
const char *snd_timer_info_get_name(snd_timer_info_t * info);
long snd_timer_info_get_resolution(snd_timer_info_t * info);

size_t snd_timer_params_sizeof(void);
int snd_timer_params_malloc(snd_timer_params_t **ptr);
void snd_timer_params_free(snd_timer_params_t *obj);
void snd_timer_params_copy(snd_timer_params_t *dst, const snd_timer_params_t *src);

int snd_timer_params_set_auto_start(snd_timer_params_t * params, int auto_start);
int snd_timer_params_get_auto_start(snd_timer_params_t * params);
int snd_timer_params_set_exclusive(snd_timer_params_t * params, int exclusive);
int snd_timer_params_get_exclusive(snd_timer_params_t * params);
int snd_timer_params_set_early_event(snd_timer_params_t * params, int early_event);
int snd_timer_params_get_early_event(snd_timer_params_t * params);
void snd_timer_params_set_ticks(snd_timer_params_t * params, long ticks);
long snd_timer_params_get_ticks(snd_timer_params_t * params);
void snd_timer_params_set_queue_size(snd_timer_params_t * params, long queue_size);
long snd_timer_params_get_queue_size(snd_timer_params_t * params);
void snd_timer_params_set_filter(snd_timer_params_t * params, unsigned int filter);
unsigned int snd_timer_params_get_filter(snd_timer_params_t * params);

size_t snd_timer_status_sizeof(void);
int snd_timer_status_malloc(snd_timer_status_t **ptr);
void snd_timer_status_free(snd_timer_status_t *obj);
void snd_timer_status_copy(snd_timer_status_t *dst, const snd_timer_status_t *src);

long snd_timer_status_get_resolution(snd_timer_status_t * status);
long snd_timer_status_get_lost(snd_timer_status_t * status);
long snd_timer_status_get_overrun(snd_timer_status_t * status);
long snd_timer_status_get_queue(snd_timer_status_t * status);

long snd_timer_info_get_ticks(snd_timer_info_t * info);

/*************************************************************************************************/

/* seq.h */


typedef struct _snd_seq snd_seq_t;

#define SND_SEQ_OPEN_OUTPUT 1
#define SND_SEQ_OPEN_INPUT  2
#define SND_SEQ_OPEN_DUPLEX 3

#define SND_SEQ_NONBLOCK    1

typedef enum _snd_seq_type {
    SND_SEQ_TYPE_HW,
    SND_SEQ_TYPE_SHM,
    SND_SEQ_TYPE_INET       /**< network (NYI) */
} snd_seq_type_t;

#define SND_SEQ_ADDRESS_UNKNOWN     253
#define SND_SEQ_ADDRESS_SUBSCRIBERS 254
#define SND_SEQ_ADDRESS_BROADCAST   255

#define SND_SEQ_CLIENT_SYSTEM       0

int snd_seq_open(snd_seq_t **handle, const char *name, int streams, int mode);
int snd_seq_open_lconf(snd_seq_t **handle, const char *name, int streams,
                       int mode, snd_config_t *lconf);
const char *snd_seq_name(snd_seq_t *seq);
snd_seq_type_t snd_seq_type(snd_seq_t *seq);
int snd_seq_close(snd_seq_t *handle);
int snd_seq_poll_descriptors_count(snd_seq_t *handle, short events);
int snd_seq_poll_descriptors(snd_seq_t *handle, struct pollfd *pfds,
                             unsigned int space, short events);
int snd_seq_poll_descriptors_revents(snd_seq_t *seq, struct pollfd *pfds,
                                     unsigned int nfds, unsigned short *revents);
int snd_seq_nonblock(snd_seq_t *handle, int nonblock);
int snd_seq_client_id(snd_seq_t *handle);

size_t snd_seq_get_output_buffer_size(snd_seq_t *handle);
size_t snd_seq_get_input_buffer_size(snd_seq_t *handle);
int snd_seq_set_output_buffer_size(snd_seq_t *handle, size_t size);
int snd_seq_set_input_buffer_size(snd_seq_t *handle, size_t size);

typedef struct _snd_seq_system_info snd_seq_system_info_t;

size_t snd_seq_system_info_sizeof(void);
int snd_seq_system_info_malloc(snd_seq_system_info_t **ptr);
void snd_seq_system_info_free(snd_seq_system_info_t *ptr);
void snd_seq_system_info_copy(snd_seq_system_info_t *dst, const snd_seq_system_info_t *src);

int snd_seq_system_info_get_queues(const snd_seq_system_info_t *info);
int snd_seq_system_info_get_clients(const snd_seq_system_info_t *info);
int snd_seq_system_info_get_ports(const snd_seq_system_info_t *info);
int snd_seq_system_info_get_channels(const snd_seq_system_info_t *info);
int snd_seq_system_info_get_cur_clients(const snd_seq_system_info_t *info);
int snd_seq_system_info_get_cur_queues(const snd_seq_system_info_t *info);

int snd_seq_system_info(snd_seq_t *handle, snd_seq_system_info_t *info);

typedef struct _snd_seq_client_info snd_seq_client_info_t;

typedef enum snd_seq_client_type {
    SND_SEQ_USER_CLIENT     = 1,    /**< user client */
    SND_SEQ_KERNEL_CLIENT   = 2 /**< kernel client */
} snd_seq_client_type_t;

size_t snd_seq_client_info_sizeof(void);
int snd_seq_client_info_malloc(snd_seq_client_info_t **ptr);
void snd_seq_client_info_free(snd_seq_client_info_t *ptr);
void snd_seq_client_info_copy(snd_seq_client_info_t *dst, const snd_seq_client_info_t *src);

int snd_seq_client_info_get_client(const snd_seq_client_info_t *info);
snd_seq_client_type_t snd_seq_client_info_get_type(const snd_seq_client_info_t *info);
const char *snd_seq_client_info_get_name(snd_seq_client_info_t *info);
int snd_seq_client_info_get_broadcast_filter(const snd_seq_client_info_t *info);
int snd_seq_client_info_get_error_bounce(const snd_seq_client_info_t *info);
int snd_seq_client_info_get_card(const snd_seq_client_info_t *info);
int snd_seq_client_info_get_pid(const snd_seq_client_info_t *info);
const unsigned char *snd_seq_client_info_get_event_filter(const snd_seq_client_info_t *info);
int snd_seq_client_info_get_num_ports(const snd_seq_client_info_t *info);
int snd_seq_client_info_get_event_lost(const snd_seq_client_info_t *info);

void snd_seq_client_info_set_client(snd_seq_client_info_t *info, int client);
void snd_seq_client_info_set_name(snd_seq_client_info_t *info, const char *name);
void snd_seq_client_info_set_broadcast_filter(snd_seq_client_info_t *info, int val);
void snd_seq_client_info_set_error_bounce(snd_seq_client_info_t *info, int val);
void snd_seq_client_info_set_event_filter(snd_seq_client_info_t *info, unsigned char *filter);

void snd_seq_client_info_event_filter_clear(snd_seq_client_info_t *info);
void snd_seq_client_info_event_filter_add(snd_seq_client_info_t *info, int event_type);
void snd_seq_client_info_event_filter_del(snd_seq_client_info_t *info, int event_type);
int snd_seq_client_info_event_filter_check(snd_seq_client_info_t *info, int event_type);

int snd_seq_get_client_info(snd_seq_t *handle, snd_seq_client_info_t *info);
int snd_seq_get_any_client_info(snd_seq_t *handle, int client, snd_seq_client_info_t *info);
int snd_seq_set_client_info(snd_seq_t *handle, snd_seq_client_info_t *info);
int snd_seq_query_next_client(snd_seq_t *handle, snd_seq_client_info_t *info);

typedef struct _snd_seq_client_pool snd_seq_client_pool_t;

size_t snd_seq_client_pool_sizeof(void);
int snd_seq_client_pool_malloc(snd_seq_client_pool_t **ptr);
void snd_seq_client_pool_free(snd_seq_client_pool_t *ptr);
void snd_seq_client_pool_copy(snd_seq_client_pool_t *dst, const snd_seq_client_pool_t *src);

int snd_seq_client_pool_get_client(const snd_seq_client_pool_t *info);
size_t snd_seq_client_pool_get_output_pool(const snd_seq_client_pool_t *info);
size_t snd_seq_client_pool_get_input_pool(const snd_seq_client_pool_t *info);
size_t snd_seq_client_pool_get_output_room(const snd_seq_client_pool_t *info);
size_t snd_seq_client_pool_get_output_free(const snd_seq_client_pool_t *info);
size_t snd_seq_client_pool_get_input_free(const snd_seq_client_pool_t *info);
void snd_seq_client_pool_set_output_pool(snd_seq_client_pool_t *info, size_t size);
void snd_seq_client_pool_set_input_pool(snd_seq_client_pool_t *info, size_t size);
void snd_seq_client_pool_set_output_room(snd_seq_client_pool_t *info, size_t size);

int snd_seq_get_client_pool(snd_seq_t *handle, snd_seq_client_pool_t *info);
int snd_seq_set_client_pool(snd_seq_t *handle, snd_seq_client_pool_t *info);

typedef struct _snd_seq_port_info snd_seq_port_info_t;

#define SND_SEQ_PORT_SYSTEM_TIMER   0
#define SND_SEQ_PORT_SYSTEM_ANNOUNCE    1

#define SND_SEQ_PORT_CAP_READ       1
#define SND_SEQ_PORT_CAP_WRITE      2

#define SND_SEQ_PORT_CAP_SYNC_READ  4
#define SND_SEQ_PORT_CAP_SYNC_WRITE 8

#define SND_SEQ_PORT_CAP_DUPLEX     16

#define SND_SEQ_PORT_CAP_SUBS_READ  32
#define SND_SEQ_PORT_CAP_SUBS_WRITE 64
#define SND_SEQ_PORT_CAP_NO_EXPORT  128

#define SND_SEQ_PORT_TYPE_SPECIFIC  1
#define SND_SEQ_PORT_TYPE_MIDI_GENERIC  2
#define SND_SEQ_PORT_TYPE_MIDI_GM   4
#define SND_SEQ_PORT_TYPE_MIDI_GS   8
#define SND_SEQ_PORT_TYPE_MIDI_XG   16
#define SND_SEQ_PORT_TYPE_MIDI_MT32 32
#define SND_SEQ_PORT_TYPE_MIDI_GM2  64
#define SND_SEQ_PORT_TYPE_SYNTH     1024
#define SND_SEQ_PORT_TYPE_DIRECT_SAMPLE 2048
#define SND_SEQ_PORT_TYPE_SAMPLE    4096
#define SND_SEQ_PORT_TYPE_HARDWARE  65536
#define SND_SEQ_PORT_TYPE_SOFTWARE  131072
#define SND_SEQ_PORT_TYPE_SYNTHESIZER   262144
#define SND_SEQ_PORT_TYPE_PORT      524288
#define SND_SEQ_PORT_TYPE_APPLICATION   1048576

size_t snd_seq_port_info_sizeof(void);
int snd_seq_port_info_malloc(snd_seq_port_info_t **ptr);
void snd_seq_port_info_free(snd_seq_port_info_t *ptr);
void snd_seq_port_info_copy(snd_seq_port_info_t *dst, const snd_seq_port_info_t *src);

int snd_seq_port_info_get_client(const snd_seq_port_info_t *info);
int snd_seq_port_info_get_port(const snd_seq_port_info_t *info);
const snd_seq_addr_t *snd_seq_port_info_get_addr(const snd_seq_port_info_t *info);
const char *snd_seq_port_info_get_name(const snd_seq_port_info_t *info);
unsigned int snd_seq_port_info_get_capability(const snd_seq_port_info_t *info);
unsigned int snd_seq_port_info_get_type(const snd_seq_port_info_t *info);
int snd_seq_port_info_get_midi_channels(const snd_seq_port_info_t *info);
int snd_seq_port_info_get_midi_voices(const snd_seq_port_info_t *info);
int snd_seq_port_info_get_synth_voices(const snd_seq_port_info_t *info);
int snd_seq_port_info_get_read_use(const snd_seq_port_info_t *info);
int snd_seq_port_info_get_write_use(const snd_seq_port_info_t *info);
int snd_seq_port_info_get_port_specified(const snd_seq_port_info_t *info);
int snd_seq_port_info_get_timestamping(const snd_seq_port_info_t *info);
int snd_seq_port_info_get_timestamp_real(const snd_seq_port_info_t *info);
int snd_seq_port_info_get_timestamp_queue(const snd_seq_port_info_t *info);

void snd_seq_port_info_set_client(snd_seq_port_info_t *info, int client);
void snd_seq_port_info_set_port(snd_seq_port_info_t *info, int port);
void snd_seq_port_info_set_addr(snd_seq_port_info_t *info, const snd_seq_addr_t *addr);
void snd_seq_port_info_set_name(snd_seq_port_info_t *info, const char *name);
void snd_seq_port_info_set_capability(snd_seq_port_info_t *info, unsigned int capability);
void snd_seq_port_info_set_type(snd_seq_port_info_t *info, unsigned int type);
void snd_seq_port_info_set_midi_channels(snd_seq_port_info_t *info, int channels);
void snd_seq_port_info_set_midi_voices(snd_seq_port_info_t *info, int voices);
void snd_seq_port_info_set_synth_voices(snd_seq_port_info_t *info, int voices);
void snd_seq_port_info_set_port_specified(snd_seq_port_info_t *info, int val);
void snd_seq_port_info_set_timestamping(snd_seq_port_info_t *info, int enable);
void snd_seq_port_info_set_timestamp_real(snd_seq_port_info_t *info, int realtime);
void snd_seq_port_info_set_timestamp_queue(snd_seq_port_info_t *info, int queue);

int snd_seq_create_port(snd_seq_t *handle, snd_seq_port_info_t *info);
int snd_seq_delete_port(snd_seq_t *handle, int port);
int snd_seq_get_port_info(snd_seq_t *handle, int port, snd_seq_port_info_t *info);
int snd_seq_get_any_port_info(snd_seq_t *handle, int client, int port, snd_seq_port_info_t *info);
int snd_seq_set_port_info(snd_seq_t *handle, int port, snd_seq_port_info_t *info);
int snd_seq_query_next_port(snd_seq_t *handle, snd_seq_port_info_t *info);

typedef struct _snd_seq_port_subscribe snd_seq_port_subscribe_t;

size_t snd_seq_port_subscribe_sizeof(void);
int snd_seq_port_subscribe_malloc(snd_seq_port_subscribe_t **ptr);
void snd_seq_port_subscribe_free(snd_seq_port_subscribe_t *ptr);
void snd_seq_port_subscribe_copy(snd_seq_port_subscribe_t *dst,
                                 const snd_seq_port_subscribe_t *src);

const snd_seq_addr_t *snd_seq_port_subscribe_get_sender(const snd_seq_port_subscribe_t *info);
const snd_seq_addr_t *snd_seq_port_subscribe_get_dest(const snd_seq_port_subscribe_t *info);
int snd_seq_port_subscribe_get_queue(const snd_seq_port_subscribe_t *info);
int snd_seq_port_subscribe_get_exclusive(const snd_seq_port_subscribe_t *info);
int snd_seq_port_subscribe_get_time_update(const snd_seq_port_subscribe_t *info);
int snd_seq_port_subscribe_get_time_real(const snd_seq_port_subscribe_t *info);

void snd_seq_port_subscribe_set_sender(snd_seq_port_subscribe_t *info, const snd_seq_addr_t *addr);
void snd_seq_port_subscribe_set_dest(snd_seq_port_subscribe_t *info, const snd_seq_addr_t *addr);
void snd_seq_port_subscribe_set_queue(snd_seq_port_subscribe_t *info, int q);
void snd_seq_port_subscribe_set_exclusive(snd_seq_port_subscribe_t *info, int val);
void snd_seq_port_subscribe_set_time_update(snd_seq_port_subscribe_t *info, int val);
void snd_seq_port_subscribe_set_time_real(snd_seq_port_subscribe_t *info, int val);

int snd_seq_get_port_subscription(snd_seq_t *handle, snd_seq_port_subscribe_t *sub);
int snd_seq_subscribe_port(snd_seq_t *handle, snd_seq_port_subscribe_t *sub);
int snd_seq_unsubscribe_port(snd_seq_t *handle, snd_seq_port_subscribe_t *sub);

typedef struct _snd_seq_query_subscribe snd_seq_query_subscribe_t;

typedef enum {
    SND_SEQ_QUERY_SUBS_READ,    /**< query read subscriptions */
    SND_SEQ_QUERY_SUBS_WRITE    /**< query write subscriptions */
} snd_seq_query_subs_type_t;

size_t snd_seq_query_subscribe_sizeof(void);

int snd_seq_query_subscribe_malloc(snd_seq_query_subscribe_t **ptr);
void snd_seq_query_subscribe_free(snd_seq_query_subscribe_t *ptr);
void snd_seq_query_subscribe_copy(snd_seq_query_subscribe_t *dst,
                                  const snd_seq_query_subscribe_t *src);

int snd_seq_query_subscribe_get_client(const snd_seq_query_subscribe_t *info);
int snd_seq_query_subscribe_get_port(const snd_seq_query_subscribe_t *info);
const snd_seq_addr_t *snd_seq_query_subscribe_get_root(const snd_seq_query_subscribe_t *info);
snd_seq_query_subs_type_t snd_seq_query_subscribe_get_type(const snd_seq_query_subscribe_t *info);
int snd_seq_query_subscribe_get_index(const snd_seq_query_subscribe_t *info);
int snd_seq_query_subscribe_get_num_subs(const snd_seq_query_subscribe_t *info);
const snd_seq_addr_t *snd_seq_query_subscribe_get_addr(const snd_seq_query_subscribe_t *info);
int snd_seq_query_subscribe_get_queue(const snd_seq_query_subscribe_t *info);
int snd_seq_query_subscribe_get_exclusive(const snd_seq_query_subscribe_t *info);
int snd_seq_query_subscribe_get_time_update(const snd_seq_query_subscribe_t *info);
int snd_seq_query_subscribe_get_time_real(const snd_seq_query_subscribe_t *info);

void snd_seq_query_subscribe_set_client(snd_seq_query_subscribe_t *info, int client);
void snd_seq_query_subscribe_set_port(snd_seq_query_subscribe_t *info, int port);
void snd_seq_query_subscribe_set_root(snd_seq_query_subscribe_t *info, const snd_seq_addr_t *addr);
void snd_seq_query_subscribe_set_type(snd_seq_query_subscribe_t *info,
                                      snd_seq_query_subs_type_t type);
void snd_seq_query_subscribe_set_index(snd_seq_query_subscribe_t *info, int _index);

int snd_seq_query_port_subscribers(snd_seq_t *seq, snd_seq_query_subscribe_t * subs);

typedef struct _snd_seq_queue_info snd_seq_queue_info_t;
typedef struct _snd_seq_queue_status snd_seq_queue_status_t;
typedef struct _snd_seq_queue_tempo snd_seq_queue_tempo_t;
typedef struct _snd_seq_queue_timer snd_seq_queue_timer_t;

#define SND_SEQ_QUEUE_DIRECT        253

size_t snd_seq_queue_info_sizeof(void);
int snd_seq_queue_info_malloc(snd_seq_queue_info_t **ptr);
void snd_seq_queue_info_free(snd_seq_queue_info_t *ptr);
void snd_seq_queue_info_copy(snd_seq_queue_info_t *dst, const snd_seq_queue_info_t *src);

int snd_seq_queue_info_get_queue(const snd_seq_queue_info_t *info);
const char *snd_seq_queue_info_get_name(const snd_seq_queue_info_t *info);
int snd_seq_queue_info_get_owner(const snd_seq_queue_info_t *info);
int snd_seq_queue_info_get_locked(const snd_seq_queue_info_t *info);
unsigned int snd_seq_queue_info_get_flags(const snd_seq_queue_info_t *info);

void snd_seq_queue_info_set_name(snd_seq_queue_info_t *info, const char *name);
void snd_seq_queue_info_set_owner(snd_seq_queue_info_t *info, int owner);
void snd_seq_queue_info_set_locked(snd_seq_queue_info_t *info, int locked);
void snd_seq_queue_info_set_flags(snd_seq_queue_info_t *info, unsigned int flags);

int snd_seq_create_queue(snd_seq_t *seq, snd_seq_queue_info_t *info);
int snd_seq_alloc_named_queue(snd_seq_t *seq, const char *name);
int snd_seq_alloc_queue(snd_seq_t *handle);
int snd_seq_free_queue(snd_seq_t *handle, int q);
int snd_seq_get_queue_info(snd_seq_t *seq, int q, snd_seq_queue_info_t *info);
int snd_seq_set_queue_info(snd_seq_t *seq, int q, snd_seq_queue_info_t *info);
int snd_seq_query_named_queue(snd_seq_t *seq, const char *name);

int snd_seq_get_queue_usage(snd_seq_t *handle, int q);
int snd_seq_set_queue_usage(snd_seq_t *handle, int q, int used);

size_t snd_seq_queue_status_sizeof(void);
int snd_seq_queue_status_malloc(snd_seq_queue_status_t **ptr);
void snd_seq_queue_status_free(snd_seq_queue_status_t *ptr);
void snd_seq_queue_status_copy(snd_seq_queue_status_t *dst, const snd_seq_queue_status_t *src);

int snd_seq_queue_status_get_queue(const snd_seq_queue_status_t *info);
int snd_seq_queue_status_get_events(const snd_seq_queue_status_t *info);
snd_seq_tick_time_t snd_seq_queue_status_get_tick_time(const snd_seq_queue_status_t *info);
const snd_seq_real_time_t *snd_seq_queue_status_get_real_time(const snd_seq_queue_status_t *info);
unsigned int snd_seq_queue_status_get_status(const snd_seq_queue_status_t *info);

int snd_seq_get_queue_status(snd_seq_t *handle, int q, snd_seq_queue_status_t *status);

size_t snd_seq_queue_tempo_sizeof(void);
int snd_seq_queue_tempo_malloc(snd_seq_queue_tempo_t **ptr);
void snd_seq_queue_tempo_free(snd_seq_queue_tempo_t *ptr);
void snd_seq_queue_tempo_copy(snd_seq_queue_tempo_t *dst, const snd_seq_queue_tempo_t *src);

int snd_seq_queue_tempo_get_queue(const snd_seq_queue_tempo_t *info);
unsigned int snd_seq_queue_tempo_get_tempo(const snd_seq_queue_tempo_t *info);
int snd_seq_queue_tempo_get_ppq(const snd_seq_queue_tempo_t *info);
unsigned int snd_seq_queue_tempo_get_skew(const snd_seq_queue_tempo_t *info);
unsigned int snd_seq_queue_tempo_get_skew_base(const snd_seq_queue_tempo_t *info);
void snd_seq_queue_tempo_set_tempo(snd_seq_queue_tempo_t *info, unsigned int tempo);
void snd_seq_queue_tempo_set_ppq(snd_seq_queue_tempo_t *info, int ppq);
void snd_seq_queue_tempo_set_skew(snd_seq_queue_tempo_t *info, unsigned int skew);
void snd_seq_queue_tempo_set_skew_base(snd_seq_queue_tempo_t *info, unsigned int base);

int snd_seq_get_queue_tempo(snd_seq_t *handle, int q, snd_seq_queue_tempo_t *tempo);
int snd_seq_set_queue_tempo(snd_seq_t *handle, int q, snd_seq_queue_tempo_t *tempo);

typedef enum {
    SND_SEQ_TIMER_ALSA = 0,     /* ALSA timer */
    SND_SEQ_TIMER_MIDI_CLOCK = 1,   /* Midi Clock (CLOCK event) */
    SND_SEQ_TIMER_MIDI_TICK = 2 /* Midi Timer Tick (TICK event */
} snd_seq_queue_timer_type_t;

size_t snd_seq_queue_timer_sizeof(void);
int snd_seq_queue_timer_malloc(snd_seq_queue_timer_t **ptr);
void snd_seq_queue_timer_free(snd_seq_queue_timer_t *ptr);
void snd_seq_queue_timer_copy(snd_seq_queue_timer_t *dst, const snd_seq_queue_timer_t *src);

int snd_seq_queue_timer_get_queue(const snd_seq_queue_timer_t *info);
snd_seq_queue_timer_type_t snd_seq_queue_timer_get_type(const snd_seq_queue_timer_t *info);
const snd_timer_id_t *snd_seq_queue_timer_get_id(const snd_seq_queue_timer_t *info);
unsigned int snd_seq_queue_timer_get_resolution(const snd_seq_queue_timer_t *info);

void snd_seq_queue_timer_set_type(snd_seq_queue_timer_t *info, snd_seq_queue_timer_type_t type);
void snd_seq_queue_timer_set_id(snd_seq_queue_timer_t *info, const snd_timer_id_t *id);
void snd_seq_queue_timer_set_resolution(snd_seq_queue_timer_t *info, unsigned int resolution);

int snd_seq_get_queue_timer(snd_seq_t *handle, int q, snd_seq_queue_timer_t *timer);
int snd_seq_set_queue_timer(snd_seq_t *handle, int q, snd_seq_queue_timer_t *timer);

int snd_seq_free_event(snd_seq_event_t *ev);
ssize_t snd_seq_event_length(snd_seq_event_t *ev);
int snd_seq_event_output(snd_seq_t *handle, snd_seq_event_t *ev);
int snd_seq_event_output_buffer(snd_seq_t *handle, snd_seq_event_t *ev);
int snd_seq_event_output_direct(snd_seq_t *handle, snd_seq_event_t *ev);
int snd_seq_event_input(snd_seq_t *handle, snd_seq_event_t **ev);
int snd_seq_event_input_pending(snd_seq_t *seq, int fetch_sequencer);
int snd_seq_drain_output(snd_seq_t *handle);
int snd_seq_event_output_pending(snd_seq_t *seq);
int snd_seq_extract_output(snd_seq_t *handle, snd_seq_event_t **ev);
int snd_seq_drop_output(snd_seq_t *handle);
int snd_seq_drop_output_buffer(snd_seq_t *handle);
int snd_seq_drop_input(snd_seq_t *handle);
int snd_seq_drop_input_buffer(snd_seq_t *handle);

typedef struct _snd_seq_remove_events snd_seq_remove_events_t;

#define SND_SEQ_REMOVE_INPUT        1
#define SND_SEQ_REMOVE_OUTPUT       2
#define SND_SEQ_REMOVE_DEST     4
#define SND_SEQ_REMOVE_DEST_CHANNEL 8
#define SND_SEQ_REMOVE_TIME_BEFORE  16
#define SND_SEQ_REMOVE_TIME_AFTER   32
#define SND_SEQ_REMOVE_TIME_TICK    64
#define SND_SEQ_REMOVE_EVENT_TYPE   128
#define SND_SEQ_REMOVE_IGNORE_OFF   256
#define SND_SEQ_REMOVE_TAG_MATCH    512

size_t snd_seq_remove_events_sizeof(void);
int snd_seq_remove_events_malloc(snd_seq_remove_events_t **ptr);
void snd_seq_remove_events_free(snd_seq_remove_events_t *ptr);
void snd_seq_remove_events_copy(snd_seq_remove_events_t *dst, const snd_seq_remove_events_t *src);

unsigned int snd_seq_remove_events_get_condition(const snd_seq_remove_events_t *info);
int snd_seq_remove_events_get_queue(const snd_seq_remove_events_t *info);
const snd_seq_timestamp_t *snd_seq_remove_events_get_time(const snd_seq_remove_events_t *info);
const snd_seq_addr_t *snd_seq_remove_events_get_dest(const snd_seq_remove_events_t *info);
int snd_seq_remove_events_get_channel(const snd_seq_remove_events_t *info);
int snd_seq_remove_events_get_event_type(const snd_seq_remove_events_t *info);
int snd_seq_remove_events_get_tag(const snd_seq_remove_events_t *info);

void snd_seq_remove_events_set_condition(snd_seq_remove_events_t *info, unsigned int flags);
void snd_seq_remove_events_set_queue(snd_seq_remove_events_t *info, int queue);
void snd_seq_remove_events_set_time(snd_seq_remove_events_t *info,
                                    const snd_seq_timestamp_t *time);
void snd_seq_remove_events_set_dest(snd_seq_remove_events_t *info, const snd_seq_addr_t *addr);
void snd_seq_remove_events_set_channel(snd_seq_remove_events_t *info, int channel);
void snd_seq_remove_events_set_event_type(snd_seq_remove_events_t *info, int type);
void snd_seq_remove_events_set_tag(snd_seq_remove_events_t *info, int tag);

int snd_seq_remove_events(snd_seq_t *handle, snd_seq_remove_events_t *info);

void snd_seq_set_bit(int nr, void *array);
void snd_seq_unset_bit(int nr, void *array);
int snd_seq_change_bit(int nr, void *array);
int snd_seq_get_bit(int nr, void *array);

enum {
    SND_SEQ_EVFLG_RESULT,
    SND_SEQ_EVFLG_NOTE,
    SND_SEQ_EVFLG_CONTROL,
    SND_SEQ_EVFLG_QUEUE,
    SND_SEQ_EVFLG_SYSTEM,
    SND_SEQ_EVFLG_MESSAGE,
    SND_SEQ_EVFLG_CONNECTION,
    SND_SEQ_EVFLG_SAMPLE,
    SND_SEQ_EVFLG_USERS,
    SND_SEQ_EVFLG_INSTR,
    SND_SEQ_EVFLG_QUOTE,
    SND_SEQ_EVFLG_NONE,
    SND_SEQ_EVFLG_RAW,
    SND_SEQ_EVFLG_FIXED,
    SND_SEQ_EVFLG_VARIABLE,
    SND_SEQ_EVFLG_VARUSR
};

enum {
    SND_SEQ_EVFLG_NOTE_ONEARG,
    SND_SEQ_EVFLG_NOTE_TWOARG
};

enum {
    SND_SEQ_EVFLG_QUEUE_NOARG,
    SND_SEQ_EVFLG_QUEUE_TICK,
    SND_SEQ_EVFLG_QUEUE_TIME,
    SND_SEQ_EVFLG_QUEUE_VALUE
};

extern const unsigned int snd_seq_event_types[];

/*******************************************************************************************************/

/* seqmid.h */

int snd_seq_control_queue(snd_seq_t *seq, int q, int type, int value, snd_seq_event_t *ev);
int snd_seq_create_simple_port(snd_seq_t *seq, const char *name,
                   unsigned int caps, unsigned int type);
int snd_seq_delete_simple_port(snd_seq_t *seq, int port);

int snd_seq_connect_from(snd_seq_t *seq, int my_port, int src_client, int src_port);
int snd_seq_connect_to(snd_seq_t *seq, int my_port, int dest_client, int dest_port);
int snd_seq_disconnect_from(snd_seq_t *seq, int my_port, int src_client, int src_port);
int snd_seq_disconnect_to(snd_seq_t *seq, int my_port, int dest_client, int dest_port);

int snd_seq_set_client_name(snd_seq_t *seq, const char *name);
int snd_seq_set_client_event_filter(snd_seq_t *seq, int event_type);
int snd_seq_set_client_pool_output(snd_seq_t *seq, size_t size);
int snd_seq_set_client_pool_output_room(snd_seq_t *seq, size_t size);
int snd_seq_set_client_pool_input(snd_seq_t *seq, size_t size);
int snd_seq_sync_output_queue(snd_seq_t *seq);

int snd_seq_parse_address(snd_seq_t *seq, snd_seq_addr_t *addr, const char *str);

int snd_seq_reset_pool_output(snd_seq_t *seq);
int snd_seq_reset_pool_input(snd_seq_t *seq);
"""

ffi.set_source("alsa_midi._ffi_bin", C_SOURCE, libraries=["asound"])
ffi.cdef(C_DEFS_PACKED, packed=True)
ffi.cdef(C_DEFS)

if __name__ == "__main__":
    ffi.compile(verbose=True)
