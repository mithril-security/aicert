VERSION 0.7

debian-systemd:
    FROM debian:bookworm-slim

    ENV DEBIAN_FRONTEND=noninteractive

    RUN apt-get update
    RUN apt-get install --assume-yes --no-install-recommends \
        cryptsetup libcryptsetup-dev \
        git \ 
        meson \
        gcc \
        gperf \
        libcap-dev \
        libmount-dev \
        libssl-dev \
        python3-jinja2 \
        pkg-config \
        ca-certificates \
        btrfs-progs \
        bubblewrap \
        debian-archive-keyring \
        dnf \
        e2fsprogs \
        erofs-utils \
        mtools \
        ovmf \
        python3-pefile \
        python3-pyelftools \
        qemu-system-x86 \
        squashfs-tools \
        swtpm \
        systemd-container \
        xfsprogs \
        zypper
    COPY update_systemd.sh .
    RUN bash update_systemd.sh
    SAVE IMAGE debian-systemd

mithril-os:
    FROM +debian-systemd

    RUN apt install --assume-yes --no-install-recommends \
        python3-pip python3-venv pipx
    RUN pipx install git+https://github.com/systemd/mkosi.git@466851c60166954f5c185497486546d419ceaca3


    RUN  apt-get install --assume-yes --no-install-recommends dosfstools cpio zstd
    WORKDIR /workdir

    COPY mithril-os/render_template ./render_template
    RUN pipx install render_template/

    COPY mithril-os/*.yaml .

    ARG OS_CONFIG="config.yaml"
    
    WORKDIR /workdir/initrd
    CACHE mkosi.cache
    COPY mithril-os/mkosi/initrd .
    RUN /root/.local/bin/render_template "../$OS_CONFIG" mkosi.conf.j2
    
    RUN --privileged /root/.local/bin/mkosi

    SAVE ARTIFACT image AS LOCAL local/initrd_image.cpio.zst
    SAVE ARTIFACT image.manifest AS LOCAL local/initrd.manifest

    # RUN --privileged error

    WORKDIR /workdir/rootfs/mkosi.extra/opt/container-images

    WITH DOCKER --pull caddy:latest
        RUN docker save -o caddy-image.tar caddy:latest
    END

    WITH DOCKER --load aicert-server:latest=+aicert-server-image
        RUN docker save -o aicert-server-image.tar aicert-server:latest
    END

    WITH DOCKER --load aicert-base:latest=+aicert-base-image
        RUN docker save -o aicert-base-image.tar aicert-base:latest
    END

    WITH DOCKER --pull winglian/axolotl:main-py3.11-cu121-2.1.2
        RUN docker tag winglian/axolotl:main-py3.11-cu121-2.1.2 axolotl:latest && \
            docker save -o axolotl.tar axolotl:latest
    END


    WORKDIR /workdir/rootfs
    CACHE mkosi.cache

    COPY mithril-os/mkosi/rootfs .
    RUN /root/.local/bin/render_template "../$OS_CONFIG" mkosi.conf.j2

    # RUN --privileged error

    RUN --privileged /root/.local/bin/mkosi

    # RUN  --privileged error

    SAVE ARTIFACT image.raw AS LOCAL local/os_disk.raw
    SAVE ARTIFACT image.manifest AS LOCAL local/os_disk.manifest


aicert-server-image:
    FROM DOCKERFILE server/aicert_server
    SAVE IMAGE aicert-server

aicert-base-image:
    FROM DOCKERFILE server/aicert_server/base_image
    SAVE IMAGE aicert-base

