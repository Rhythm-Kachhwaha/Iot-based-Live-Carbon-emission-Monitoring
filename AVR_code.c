/* Flash the code using a programmer into the ATMEGA 328PB*/

#include <avr/io.h>
#include <avr/interrupt.h>
#include <string.h>
#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>


/*                                CONFIGURATION CONSTANTS                                  */


#define UART0_BAUD       2400UL             /* Energy meter baud rate                */
#define UART1_BAUD       38400UL            /* GPRS modem baud rate                  */

#define APN_STRING       "airtelgprs.com"   /* <<< CHANGE TO YOUR APN                */
#define URL_BASE         "http://2e40139af09b.ngrok-free.app/meter" /* <<< EDIT URL keeping the /meter */

#define COMMAND_DELAY_MS 2000               /* 2 second delay between AT commands   */
#define HTTP_DELAY_MS    1500               /* 1.5 second delay between HTTP steps  */


/*                                  METER DATA LAYOUT                                      */


typedef enum
{
    IDX_VOLTAGE              = 0,           /* Voltage (2 bytes, /100 for actual)   */
    IDX_CURRENT              = 2,           /* Current (2 bytes, /1000 for actual)  */
    IDX_POWER_FACTOR         = 4,           /* Power factor (1 byte, /100)          */
    IDX_LOAD_KW              = 5,           /* Load (3 bytes, /100000 for actual)   */
    IDX_KWH_TOTAL            = 11,          /* Total kWh (3 bytes, /100)            */
    IDX_DATE                 = 29,          /* Date                                  */
    IDX_MONTH                = 30,          /* Month                                 */
    IDX_YEAR                 = 31,          /* Year                                  */
    IDX_HOUR                 = 32,          /* Hour                                  */
    IDX_MINUTE               = 33,          /* Minute                                */
    IDX_SECOND               = 34,          /* Second                                */
    IDX_FREQUENCY            = 35,          /* Frequency (2 bytes, /10)             */
    IDX_FRAME_END            = 43           /* Frame end marker (should be 0xDD)    */
} meter_index_t;


/*                                    GLOBAL VARIABLES                                     */


static volatile uint8_t  meterBuf[44];      /* Raw 44-byte meter frame               */
static volatile uint8_t  meterIdx   = 0;    /* Current write position in frame       */
static volatile bool     frameReady = false;/* New complete frame available          */

static volatile uint32_t tick10ms   = 0;    /* 10ms timer tick counter               */
static volatile uint32_t millisCnt  = 0;    /* Millisecond counter (10ms resolution) */


/*                                 TIMING AND UART HELPERS                                 */


/** Get current millisecond count (10ms resolution) */
static inline uint32_t millis(void) { return millisCnt; }

/** Send single byte to UART0 (meter interface) */
static inline void uart0_send(uint8_t byte) 
{ 
    while (!(UCSR0A & (1<<UDRE0))); 
    UDR0 = byte; 
}

/** Send single byte to UART1 (GPRS modem) */
static inline void uart1_send_byte(uint8_t byte) 
{ 
    while (!(UCSR1A & (1<<UDRE1))); 
    UDR1 = byte; 
}

/** Send string to UART1 (GPRS modem) */
static void uart1_send_str(const char *str)
{
    while (*str) { 
        uart1_send_byte(*str++); 
    }
}


/*                                   INTERRUPT HANDLERS                                    */


/**
 * Timer0 Overflow Interrupt - 10ms tick generator
 * Provides timing base for state machine delays
 */
ISR(TIMER0_OVF_vect)
{
    TCNT0 = 176;                            /* Reload for next 10ms period          */
    ++tick10ms;
    millisCnt += 10;
}

/**
 * UART0 Receive Interrupt - Energy meter data input
 * Collects 44-byte binary frames from digital energy meter
 */
ISR(USART0_RX_vect)
{
    uint8_t byte = UDR0;
    meterBuf[meterIdx++] = byte;

    if (meterIdx == 44)                     /* Complete frame received               */
    {
        if (meterBuf[IDX_FRAME_END] == 0xDD) /* Validate frame end marker           */
            frameReady = true;

        meterIdx = 0;                       /* Reset for next frame                 */
    }
}

/**
 * UART1 Receive Interrupt - GPRS modem responses
 * We don't process responses in this simplified version,
 * but keep interrupt enabled to prevent buffer overflow
 */
ISR(USART1_RX_vect)
{
    volatile uint8_t dummy = UDR1;          /* Read and discard received data       */
    (void)dummy;                            /* Suppress unused variable warning     */
}


/*                                   METER DATA HELPERS                                    */


/** Extract 16-bit value from meter buffer at given index */
static inline uint16_t get_u16(uint8_t idx)
{
    return ((uint16_t)meterBuf[idx] << 8) | meterBuf[idx + 1];
}

/** Extract 24-bit value from meter buffer at given index */
static inline uint32_t get_u24(uint8_t idx)
{
    return ((uint32_t)meterBuf[idx] << 16) |
           ((uint32_t)meterBuf[idx + 1] << 8) |
            (uint32_t)meterBuf[idx + 2];
}


/*                              GPRS INITIALIZATION STATE MACHINE                          */


typedef enum
{
    GPRS_IDLE,                              /* Initial state                         */
    GPRS_AT,                               /* Send AT command                       */
    GPRS_ATE0,                             /* Turn off echo                         */
    GPRS_CPIN,                             /* Check SIM status                      */
    GPRS_CREG,                             /* Check network registration           */
    GPRS_CSQ,                              /* Check signal quality                  */
    GPRS_APN,                              /* Set APN                               */
    GPRS_ATTACH,                           /* Attach to GPRS                       */
    GPRS_NETOPEN,                          /* Open network connection               */
    GPRS_READY                             /* GPRS initialization complete          */
} gprs_state_t;

static gprs_state_t gprsState = GPRS_IDLE;
static uint32_t     gprsTimer = 0;
static bool         gprsReady = false;

/**
 * GPRS Initialization State Machine
 * Sends AT commands with timer-based delays, no response checking
 */
static void gprs_fsm(void)
{
    if (gprsReady) return;                  /* Already initialized                   */

    uint32_t now = millis();
    
    switch (gprsState)
    {
        case GPRS_IDLE:
            uart1_send_str("AT\r\n");       /* Test AT communication                 */
            gprsTimer = now;
            gprsState = GPRS_AT;
            break;

        case GPRS_AT:
            if ((now - gprsTimer) >= COMMAND_DELAY_MS)
            {
                uart1_send_str("ATE0\r\n"); /* Turn off command echo                 */
                gprsTimer = now;
                gprsState = GPRS_ATE0;
            }
            break;

        case GPRS_ATE0:
            if ((now - gprsTimer) >= COMMAND_DELAY_MS)
            {
                uart1_send_str("AT+CPIN?\r\n"); /*Check SIM card status*/
                gprsTimer = now;
                gprsState = GPRS_CPIN;
            }
            break;

        case GPRS_CPIN:
            if ((now - gprsTimer) >= COMMAND_DELAY_MS)
            {
                uart1_send_str("AT+CREG?\r\n"); /* Check network registration*/
                gprsTimer = now;
                gprsState = GPRS_CREG;
            }
            break;

        case GPRS_CREG:
            if ((now - gprsTimer) >= COMMAND_DELAY_MS)
            {
                uart1_send_str("AT+CSQ\r\n");   /* Check signal quality              */
                gprsTimer = now;
                gprsState = GPRS_CSQ;
            }
            break;

        case GPRS_CSQ:
            if ((now - gprsTimer) >= COMMAND_DELAY_MS)
            {
                uart1_send_str("AT+CGDCONT=1,\"IP\",\"" APN_STRING "\"\r\n"); /* Set APN */
                gprsTimer = now;
                gprsState = GPRS_APN;
            }
            break;

        case GPRS_APN:
            if ((now - gprsTimer) >= COMMAND_DELAY_MS)
            {
                uart1_send_str("AT+CGATT=1\r\n"); /* Attach to GPRS network            */
                gprsTimer = now;
                gprsState = GPRS_ATTACH;
            }
            break;

        case GPRS_ATTACH:
            if ((now - gprsTimer) >= COMMAND_DELAY_MS)
            {
                uart1_send_str("AT+NETOPEN\r\n");  /* Open network connection           */
                gprsTimer = now;
                gprsState = GPRS_NETOPEN;
            }
            break;

        case GPRS_NETOPEN:
            if ((now - gprsTimer) >= COMMAND_DELAY_MS)
            {
                gprsReady = true;               /* Mark GPRS as ready                */
                gprsState = GPRS_READY;
            }
            break;

        case GPRS_READY:
            /* Stay in this state - GPRS ready for HTTP operations */
            break;
    }
}


/*                                HTTP TRANSMISSION STATE MACHINE                          */


typedef enum
{
    HTTP_IDLE,                              /* Waiting for data to send              */
    HTTP_TERM,                              /* Terminate any existing HTTP session   */
    HTTP_INIT,                              /* Initialize HTTP service               */
    HTTP_CID,                               /* Set connection ID                     */
    HTTP_URL,                               /* Set target URL                        */
    HTTP_ACTION,                            /* Execute HTTP GET request             */
    HTTP_COMPLETE                           /* HTTP transmission complete            */
} http_state_t;

static http_state_t httpState = HTTP_IDLE;
static uint32_t     httpTimer = 0;
static char         httpUrl[256];           /* Buffer for complete URL               */

/**
 * Build HTTP GET URL with current meter data
 */
static void build_http_url(void)
{
    /* Extract and convert meter values */
    float voltage = get_u16(IDX_VOLTAGE) / 100.0f;
    float current = get_u16(IDX_CURRENT) / 1000.0f;
    float pf = meterBuf[IDX_POWER_FACTOR] / 100.0f;
    float load = get_u24(IDX_LOAD_KW) / 100000.0f;
    float kwh = get_u24(IDX_KWH_TOTAL) / 100.0f;
    float freq = get_u16(IDX_FREQUENCY) / 10.0f;

    /* Build URL with compact parameter names to save space */
    snprintf(httpUrl, sizeof(httpUrl),
        URL_BASE "?v=%.2f&c=%.3f&pf=%.2f&l=%.5f&k=%.2f&f=%.1f"
                 "&d=%02u-%02u-%02u%%20%02u:%02u:%02u&s=atmega328pb",
        voltage, current, pf, load, kwh, freq,
        meterBuf[IDX_DATE], meterBuf[IDX_MONTH], meterBuf[IDX_YEAR],
        meterBuf[IDX_HOUR], meterBuf[IDX_MINUTE], meterBuf[IDX_SECOND]);
}

/**
 * HTTP Transmission State Machine
 * Sends meter data via HTTP GET request
 */
static void http_fsm(void)
{
    if (!gprsReady || !frameReady) return; /* Wait for GPRS ready and new data      */

    uint32_t now = millis();
    
    switch (httpState)
    {
        case HTTP_IDLE:
            build_http_url();               /* Prepare URL with current meter data   */
            uart1_send_str("AT+HTTPTERM\r\n"); /* Ensure clean HTTP state            */
            httpTimer = now;
            httpState = HTTP_TERM;
            break;

        case HTTP_TERM:
            if ((now - httpTimer) >= HTTP_DELAY_MS)
            {
                uart1_send_str("AT+HTTPINIT\r\n"); /* Initialize HTTP service          */
                httpTimer = now;
                httpState = HTTP_INIT;
            }
            break;

        case HTTP_INIT:
            if ((now - httpTimer) >= HTTP_DELAY_MS)
            {
                uart1_send_str("AT+HTTPPARA=\"CID\",1\r\n"); /* Set connection ID      */
                httpTimer = now;
                httpState = HTTP_CID;
            }
            break;

        case HTTP_CID:
            if ((now - httpTimer) >= HTTP_DELAY_MS)
            {
                uart1_send_str("AT+HTTPPARA=\"URL\",\""); /* Start URL parameter      */
                uart1_send_str(httpUrl);                    /* Send complete URL        */
                uart1_send_str("\"\r\n");                  /* End URL parameter        */
                httpTimer = now;
                httpState = HTTP_URL;
            }
            break;

        case HTTP_URL:
            if ((now - httpTimer) >= HTTP_DELAY_MS)
            {
                uart1_send_str("AT+HTTPACTION=0\r\n"); /* Execute HTTP GET request     */
                httpTimer = now;
                httpState = HTTP_ACTION;
            }
            break;

        case HTTP_ACTION:
            if ((now - httpTimer) >= (HTTP_DELAY_MS * 2)) /* Give extra time for HTTP */
            {
                frameReady = false;         /* Mark current frame as processed       */
                httpState = HTTP_COMPLETE;
            }
            break;

        case HTTP_COMPLETE:
            if ((now - httpTimer) >= HTTP_DELAY_MS)
            {
                httpState = HTTP_IDLE;      /* Return to idle, ready for next frame  */
            }
            break;
    }
}


/*                                  HARDWARE INITIALIZATION                                */

/** Initialize UART0 for energy meter communication (2400 baud) */
static void uart0_init(void)
{
    uint16_t ubrr = (F_CPU / (16UL * UART0_BAUD)) - 1;
    UBRR0H = ubrr >> 8;
    UBRR0L = ubrr & 0xFF;
    UCSR0B = (1 << RXEN0) | (1 << TXEN0) | (1 << RXCIE0); /* Enable RX interrupt */
    UCSR0C = (1 << UCSZ00) | (1 << UCSZ01);               /* 8-bit, no parity, 1 stop */
}

/** Initialize UART1 for GPRS modem communication (38400 baud) */
static void uart1_init(void)
{
    uint16_t ubrr = (F_CPU / (16UL * UART1_BAUD)) - 1;
    UBRR1H = ubrr >> 8;
    UBRR1L = ubrr & 0xFF;
    UCSR1B = (1 << RXEN1) | (1 << TXEN1) | (1 << RXCIE1); /* Enable RX interrupt */
    UCSR1C = (1 << UCSZ10) | (1 << UCSZ11);               /* 8-bit, no parity, 1 stop */
}

/** Initialize Timer0 for 10ms periodic interrupts */
static void timer0_init(void)
{
    TCCR0B = (1 << CS02) | (1 << CS00);    /* Prescaler 1024                        */
    TCNT0 = 176;                           /* Preload for ~10ms overflow @ 16MHz   */
    TIMSK0 = (1 << TOIE0);                 /* Enable overflow interrupt             */
}


/*                                      MAIN PROGRAM                                       */

int main(void)
{
    /* Initialize hardware peripherals */
    uart0_init();                           /* Energy meter interface                */
    uart1_init();                           /* GPRS modem interface                  */
    timer0_init();                          /* System timing                         */
    
    /* Configure status LED on PB1 */
    DDRB |= (1 << 1);                       /* Set PB1 as output                    */
    PORTB |= (1 << 1);                      /* Turn on LED initially                 */
    
    sei();                                  /* Enable global interrupts              */

    uint16_t meterKickTimer = 0;            /* Timer for meter polling               */

    /* Main program loop */
    for (;;)
    {
        /* Send meter polling command every ~1 second (100 * 10ms) */
        if ((uint16_t)(tick10ms - meterKickTimer) >= 100)
        {
            meterKickTimer = tick10ms;
            PORTB ^= (1 << 1);              /* Toggle heartbeat LED                  */
            
            /* Reset meter frame collection and send poll command */
            meterIdx = 0;
            uart0_send(0xCC);               /* Meter poll command sequence           */
            uart0_send(0x91);
            uart0_send(0xDD);
        }

        /* Service state machines */
        gprs_fsm();                         /* Handle GPRS initialization           */
        http_fsm();                         /* Handle HTTP data transmission        */
    }
}

