FROM n8nio/n8n:1.88.0

USER root

RUN apk add --no-cache python3 py3-pip && \
    pip3 install pandas requests --break-system-packages

RUN mkdir -p /home/node/.n8n && \
    chown -R node:node /home/node/.n8n

USER node

ENTRYPOINT ["n8n"]
CMD ["start"]